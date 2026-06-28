"""Full-flow E2E test with REAL LLM calls via 9router (port 20228, model 4omc).

Hits the LIVE gateway at localhost:8001 — no mocks, no TestClient.
Each scenario: login -> create run -> poll -> approve Gate 1 -> poll -> approve Gate 2 -> poll -> verify.

Usage:
    uv run python scripts/test_e2e_real_llm.py
    uv run python scripts/test_e2e_real_llm.py --scenario math_simple
    uv run python scripts/test_e2e_real_llm.py --force   # skip 9router URL check
    uv run python scripts/test_e2e_real_llm.py --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

# ── Config ──────────────────────────────────────────────────────────────────
GATEWAY = "http://localhost:8001"
DEFAULT_TIMEOUT_S = 900
POLL_INTERVAL_S = 5
EXPECTED_PORT = "20228"
TERMINAL_STATUSES = frozenset({"completed", "failed"})
GATE_STATUSES = frozenset({"awaiting_approval", "awaiting_content_approval"})
BLUEPRINT_GATE = "blueprint_approval"
CONTENT_GATE = "content_approval"


@dataclass
class GateApproval:
    gate: str
    status: str
    timestamp_s: float
    elapsed_s: float


@dataclass
class ScenarioResult:
    name: str
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    steps: list[str] = field(default_factory=list)
    run_id: str = ""
    total_seconds: float = 0.0
    error_detail: str = ""
    artifact_count: int = 0
    artifact_types: list[str] = field(default_factory=list)
    gate_approvals: list[GateApproval] = field(default_factory=list)
    step_timings: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.failed == 0

    @property
    def status_label(self) -> str:
        return "PASS" if self.ok else "FAIL"

    @property
    def verdict(self) -> str:
        if self.ok:
            return f"✅ PASS ({self.passed}/{self.passed + self.skipped})"
        return f"❌ FAIL ({self.passed} passed, {self.failed} failed, {self.skipped} skipped)"


# ── Scenarios ───────────────────────────────────────────────────────────────

SCENARIOS: dict[str, dict[str, Any]] = {
    "math_simple": {
        "name": "Math — Simple Fractions (Grade 5)",
        "raw_request": "Dạy phân số bằng nhau cho lớp 5. Thời lượng 45 phút.",
        "class_info": {"grade": 5, "subject": "math", "student_count": 30},
    },
    "english_reading": {
        "name": "English — Reading Comprehension (Grade 6)",
        "raw_request": (
            "Teach reading comprehension for Grade 6 students. "
            "Topic: 'The Water Cycle'. Duration: 40 minutes. "
            "Include vocabulary and comprehension questions."
        ),
        "class_info": {"grade": 6, "subject": "english", "student_count": 25},
    },
    "vietnamese_science": {
        "name": "Vietnamese Science — Photosynthesis (Grade 7)",
        "raw_request": (
            "Bài giảng Quang hợp cho lớp 7. Thời lượng 45 phút. "
            "Bao gồm lý thuyết, thực hành quan sát, và bài tập."
        ),
        "class_info": {"grade": 7, "subject": "science", "student_count": 35},
    },
    "math_edge_short": {
        "name": "Edge Case — Minimal Input",
        "raw_request": "Teach multiplication tables.",
        "class_info": {"grade": 3, "subject": "math", "student_count": 20},
    },
    "math_edge_long": {
        "name": "Edge Case — Maximal Detailed Input",
        "raw_request": (
            "Create a comprehensive teaching pack for advanced mathematics. "
            "Topic: Introduction to Quadratic Equations and the Quadratic Formula. "
            "Grade level: 8. Subject: Mathematics. Duration: 60 minutes. "
            "Student count: 32. Language: English. "
            "Requirements: (1) Backward design with Bloom's taxonomy, ≥3 levels. "
            "(2) Gagné's 9 Events. (3) ≥3 objectives: Remember, Apply, Analyze. "
            "(4) Prerequisite assessment. (5) Formative checks every 10min. "
            "(6) Differentiated for visual/auditory/kinesthetic. "
            "(7) Real-world physics/engineering applications. "
            "(8) Quiz: 3 MCQ, 2 fill-blank, 2 short-answer, 1 essay. "
            "(9) Worksheet: 10 problems, increasing difficulty. "
            "(10) Ocean theme."
        ),
        "class_info": {"grade": 8, "subject": "math", "student_count": 32, "language": "en"},
    },
}


# ── HTTP helpers ────────────────────────────────────────────────────────────


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client) -> str:
    r = client.post(f"{GATEWAY}/auth/login", json={"username": "teacher1", "password": "any"})
    r.raise_for_status()
    return r.json()["access_token"]


def create_run(client: httpx.Client, token: str, scenario: dict[str, Any]) -> dict[str, Any]:
    r = client.post(f"{GATEWAY}/run", json={
        "raw_request": scenario["raw_request"],
        "class_info": scenario["class_info"],
        "teacher_id": "u-001",
    }, headers=_auth(token))
    r.raise_for_status()
    return r.json()


def approve_gate(client: httpx.Client, token: str, run_id: str) -> dict[str, Any]:
    r = client.post(f"{GATEWAY}/run/{run_id}/approve",
                     json={"action": "approve", "feedback": "Approved for E2E testing"},
                     headers=_auth(token))
    r.raise_for_status()
    return r.json()


def get_status(client: httpx.Client, token: str, run_id: str) -> dict[str, Any]:
    r = client.get(f"{GATEWAY}/run/{run_id}", headers=_auth(token))
    r.raise_for_status()
    return r.json()


def get_artifacts(client: httpx.Client, token: str, run_id: str) -> list[dict[str, Any]]:
    r = client.get(f"{GATEWAY}/run/{run_id}/artifacts", headers=_auth(token))
    r.raise_for_status()
    return r.json()


# ── Gate / state detection ──────────────────────────────────────────────────


def extract_interrupt_gate(state: dict[str, Any]) -> str | None:
    """Extract gate type from __interrupt__ list in state."""
    interrupt_list = state.get("__interrupt__")
    if not interrupt_list or not isinstance(interrupt_list, list) or not interrupt_list:
        return None
    raw = interrupt_list[0]
    value = getattr(raw, "value", None) or (raw.get("value", raw) if isinstance(raw, dict) else None)
    if not isinstance(value, dict):
        return None
    gate = value.get("gate")
    return gate if isinstance(gate, str) else None


def poll_until_gate_or_terminal(
    client: httpx.Client, token: str, run_id: str, timeout_s: float, start: float,
) -> dict[str, Any]:
    """Poll GET /run/{id} until a gate, terminal status, or timeout."""
    while True:
        if time.monotonic() - start > timeout_s:
            raise TimeoutError(f"Timed out after {timeout_s}s")
        try:
            data = get_status(client, token, run_id)
        except httpx.HTTPError as exc:
            print(f"    ⚠️  Poll error: {exc}, retrying...")
            time.sleep(POLL_INTERVAL_S)
            continue
        status = data.get("status", "")
        gate = extract_interrupt_gate(data.get("state", {}))
        if status in TERMINAL_STATUSES or gate is not None or status in GATE_STATUSES:
            return data
        time.sleep(POLL_INTERVAL_S)


# ── Scenario runner ─────────────────────────────────────────────────────────


class ScenarioContext:
    """Mutable context for a single scenario run — collects checks and timings."""

    def __init__(self, name: str) -> None:
        self.result = ScenarioResult(name=name)
        self.t0 = time.monotonic()

    def check(self, step: str, ok: bool, detail: str = "") -> None:
        r = self.result
        if ok:
            r.passed += 1
            r.steps.append(f"  ✅ {step}: {detail}")
        else:
            r.failed += 1
            r.steps.append(f"  ❌ {step}: {detail}")

    def timing(self, step: str, elapsed: float) -> None:
        self.result.step_timings[step] = round(elapsed, 1)

    def approve_gate_action(
        self, client: httpx.Client, token: str, run_id: str, gate: str,
        step_label: str,
    ) -> bool:
        """POST approve for a gate. Returns True on success."""
        ctx = self
        print(f"  👍 Approving {step_label}...")
        t = time.monotonic()
        try:
            data = approve_gate(client, token, run_id)
            elapsed = time.monotonic() - t
            ctx.timing(f"approve_{gate}", elapsed)
            ok = data.get("status") == "resumed"
            ctx.check(step_label, ok, f"elapsed={elapsed:.1f}s")
            ctx.result.gate_approvals.append(GateApproval(
                gate=gate, status=data.get("status", ""),
                timestamp_s=round(time.monotonic() - ctx.t0, 1), elapsed_s=round(elapsed, 1),
            ))
            return ok
        except (httpx.HTTPStatusError, Exception) as e:
            elapsed = time.monotonic() - t
            ctx.timing(f"approve_{gate}", elapsed)
            detail = f"{type(e).__name__}: {e}" if not isinstance(e, httpx.HTTPStatusError) \
                else f"status={e.response.status_code}"
            if isinstance(e, httpx.HTTPStatusError):
                ctx.result.error_detail = e.response.text[:500]
            ctx.check(step_label, False, f"{detail}, elapsed={elapsed:.1f}s")
            return False


def run_scenario(
    scenario_key: str, scenario: dict[str, Any], client: httpx.Client,
    token: str, timeout_s: float,
) -> ScenarioResult:
    ctx = ScenarioContext(scenario["name"])
    result = ctx.result

    print(f"\n{'─' * 60}")
    print(f"  📋 {scenario['name']}")
    print(f"  Request: {scenario['raw_request'][:80]}...")
    print(f"{'─' * 60}")

    # ── Step 1: Health ──────────────────────────────────────────────────
    print("  🏥 Health check...")
    try:
        r = client.get(f"{GATEWAY}/health")
        ctx.check("Health", r.status_code == 200, f"status={r.status_code}")
    except Exception as e:
        ctx.check("Health", False, f"error={e}")
        result.total_seconds = round(time.monotonic() - ctx.t0, 1)
        return result

    # ── Step 2: Create run ──────────────────────────────────────────────
    print("  📝 Creating run → planner agent (real LLM)...")
    t1 = time.monotonic()
    try:
        data = create_run(client, token, scenario)
        elapsed = time.monotonic() - t1
        ctx.timing("create_run", elapsed)
        run_id = data.get("run_id", "")
        status = data.get("status", "")
        state = data.get("state", {})
        result.run_id = run_id
        ctx.check(
            "Create run",
            status in ("awaiting_approval", "awaiting_content_approval", "running"),
            f"status={status}, has_plan={bool(state.get('lesson_plan'))}, "
            f"elapsed={elapsed:.1f}s, run_id={run_id[:12]}...",
        )
    except (httpx.HTTPStatusError, Exception) as e:
        elapsed = time.monotonic() - t1
        ctx.timing("create_run", elapsed)
        detail = f"status={e.response.status_code}" if isinstance(e, httpx.HTTPStatusError) \
            else f"{type(e).__name__}: {e}"
        if isinstance(e, httpx.HTTPStatusError):
            result.error_detail = e.response.text[:500]
        ctx.check("Create run", False, f"{detail}, elapsed={elapsed:.1f}s")
        result.total_seconds = round(time.monotonic() - ctx.t0, 1)
        return result

    # ── Step 2b: Plan quality ───────────────────────────────────────────
    plan = state.get("lesson_plan", {})
    if plan:
        ctx.check("Plan quality", bool(plan.get("topic") and plan.get("learning_objectives")),
                  f"topic='{plan.get('topic', '')[:50]}', "
                  f"objectives={len(plan.get('learning_objectives', []))}")
    else:
        ctx.check("Plan quality", False, "no lesson_plan in state")

    # ── Step 3: Gate 1 (blueprint) ─────────────────────────────────────
    current_status = data.get("status", "")
    current_state = state

    if current_status in GATE_STATUSES and extract_interrupt_gate(current_state) == BLUEPRINT_GATE:
        ctx.approve_gate_action(client, token, run_id, BLUEPRINT_GATE, "Approve Gate 1")
    elif current_status not in TERMINAL_STATUSES:
        print("  ⏳ Polling for blueprint gate...")
        t_poll = time.monotonic()
        try:
            data = poll_until_gate_or_terminal(client, token, run_id, timeout_s, time.monotonic())
            ctx.timing("poll_to_gate1", time.monotonic() - t_poll)
            current_status, current_state = data.get("status", ""), data.get("state", {})
            gate = extract_interrupt_gate(current_state)
            print(f"    → status={current_status}, gate={gate}")
            if gate == BLUEPRINT_GATE:
                ctx.approve_gate_action(client, token, run_id, BLUEPRINT_GATE, "Approve Gate 1")
            elif current_status in TERMINAL_STATUSES:
                ctx.check("Gate 1", False, f"terminated ({current_status}) before gate")
                result.total_seconds = round(time.monotonic() - ctx.t0, 1)
                return result
            else:
                result.steps.append(f"  ⏭️  Blueprint gate: skipped ({current_status})")
                result.skipped += 1
        except TimeoutError as e:
            ctx.timing("poll_to_gate1", time.monotonic() - t_poll)
            ctx.check("Poll to Gate 1", False, f"timeout: {e}")
            result.total_seconds = round(time.monotonic() - ctx.t0, 1)
            return result

    # ── Step 4: Gate 2 (content approval) ──────────────────────────────
    print("  ⏳ Polling for content gate or completion...")
    t4 = time.monotonic()
    try:
        data = poll_until_gate_or_terminal(client, token, run_id, timeout_s, time.monotonic())
        ctx.timing("poll_to_gate2", time.monotonic() - t4)
        current_status = data.get("status", "")
        gate = extract_interrupt_gate(data.get("state", {}))
        print(f"    → status={current_status}, gate={gate}")
    except TimeoutError as e:
        ctx.timing("poll_to_gate2", time.monotonic() - t4)
        ctx.check("Poll to Gate 2", False, f"timeout: {e}")
        result.total_seconds = round(time.monotonic() - ctx.t0, 1)
        return result

    if gate == CONTENT_GATE:
        ctx.approve_gate_action(client, token, run_id, CONTENT_GATE, "Approve Gate 2")
    elif current_status in TERMINAL_STATUSES:
        result.steps.append(f"  ⏭️  Content gate: skipped ({current_status})")
        result.skipped += 1
    else:
        result.steps.append(f"  ⏭️  Content gate: skipped ({current_status})")
        result.skipped += 1

    # ── Step 5: Final poll ──────────────────────────────────────────────
    if current_status not in TERMINAL_STATUSES:
        print("  ⏳ Polling for final completion...")
        t6 = time.monotonic()
        try:
            data = poll_until_gate_or_terminal(client, token, run_id, timeout_s, time.monotonic())
            ctx.timing("poll_final", time.monotonic() - t6)
            current_status = data.get("status", "")
        except TimeoutError as e:
            ctx.timing("poll_final", time.monotonic() - t6)
            ctx.check("Final completion", False, f"timeout: {e}")
            result.total_seconds = round(time.monotonic() - ctx.t0, 1)
            return result

    # ── Step 6: Final status ────────────────────────────────────────────
    print("  🏁 Checking final status...")
    ctx.check("Final status", current_status == "completed", f"status={current_status}")

    # ── Step 7: Artifacts ───────────────────────────────────────────────
    print("  📦 Checking artifacts...")
    try:
        artifacts = get_artifacts(client, token, run_id)
        count = len(artifacts)
        types = [a.get("artifact_type", "?") for a in artifacts if isinstance(a, dict)]
        result.artifact_count, result.artifact_types = count, types
        ctx.check("Artifacts", count > 0, f"count={count}, types={types}")
        for art in artifacts:
            if isinstance(art, dict):
                result.steps.append(
                    f"  📄 {art.get('artifact_type', '?')}: "
                    f"title='{art.get('title', '')[:60]}', sections={len(art.get('sections', []))}"
                )
    except (httpx.HTTPStatusError, Exception) as e:
        detail = f"HTTP {e.response.status_code}" if isinstance(e, httpx.HTTPStatusError) else str(e)
        ctx.check("Artifacts", False, detail)

    result.total_seconds = round(time.monotonic() - ctx.t0, 1)
    return result


# ── URL check ───────────────────────────────────────────────────────────────


def check_9router_url(force: bool) -> str | None:
    """Check LLM_BASE_URL points to 9router :20228. Exits if invalid and not --force."""
    url = os.environ.get("LLM_BASE_URL", "")
    if not url:
        print("⚠️  LLM_BASE_URL not set — using gateway default (no check)")
        return url
    if EXPECTED_PORT in url:
        return url
    if force:
        print(f"⚠️  --force: proceeding with LLM_BASE_URL={url} (expected :{EXPECTED_PORT})")
        return url
    print(f"❌ LLM_BASE_URL={url} does not contain :{EXPECTED_PORT}")
    print(f"   Expected 9router sidecar at port {EXPECTED_PORT}.")
    print(f"   Use --force to override this check.")
    sys.exit(1)


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Real LLM E2E test — 9router:20228, with gate approval handling"
    )
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()) + ["all"],
                        default="all", help="Which scenario to run (default: all)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                        help=f"Per-scenario timeout in seconds (default: {DEFAULT_TIMEOUT_S})")
    parser.add_argument("--force", action="store_true",
                        help="Skip 9router URL check (allow non-:20228 LLM_BASE_URL)")
    args = parser.parse_args()

    llm_url = check_9router_url(args.force)
    timeout = httpx.Timeout(connect=10.0, read=float(args.timeout), write=10.0, pool=10.0)

    print("=" * 70)
    print("  Teaching Pack — Real LLM E2E Test")
    print("=" * 70)
    print(f"  Gateway:     {GATEWAY}")
    print(f"  LLM_BASE_URL: {llm_url or '(not set — gateway default)'}")
    print(f"  Timeout:     {args.timeout}s per scenario")
    print(f"  Scenarios:   {args.scenario}")
    print(f"  Force:       {args.force}")
    print("=" * 70)

    results: list[ScenarioResult] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        try:
            r = client.get(f"{GATEWAY}/health")
            if r.status_code != 200:
                print(f"\n❌ Gateway not healthy: {r.status_code}")
                sys.exit(1)
            print("\n✅ Gateway healthy")
        except httpx.ConnectError as e:
            print(f"\n❌ Cannot reach gateway at {GATEWAY}: {e}")
            print("   Is the gateway running? Start with: uv run uvicorn ...")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Gateway check failed: {e}")
            sys.exit(1)

        try:
            token = login(client)
            print("✅ Login successful")
        except Exception as e:
            print(f"❌ Login failed: {e}")
            sys.exit(1)

        to_run = SCENARIOS if args.scenario == "all" else {args.scenario: SCENARIOS[args.scenario]}
        for key, scenario in to_run.items():
            results.append(run_scenario(key, scenario, client, token, args.timeout))

    # ── Structured results (JSON) ───────────────────────────────────────
    structured = [{
        "scenario": r.name, "status": r.status_label, "run_id": r.run_id,
        "timing_s": r.total_seconds, "artifact_count": r.artifact_count,
        "artifact_types": r.artifact_types,
        "errors": [r.error_detail] if r.error_detail else [],
        "gate_approvals": [{"gate": g.gate, "status": g.status,
                            "timestamp_s": g.timestamp_s, "elapsed_s": g.elapsed_s}
                           for g in r.gate_approvals],
        "step_timings": r.step_timings,
    } for r in results]

    print(f"\n{'=' * 70}\n  RESULTS (structured)\n{'=' * 70}")
    print(json.dumps(structured, indent=2, ensure_ascii=False))

    print(f"\n{'=' * 70}\n  SUMMARY TABLE\n{'=' * 70}")
    print(f"  {'Scenario':<35} {'Status':<8} {'Artifacts':<12} {'Timing':<10} {'Gates':<6} {'Errors'}")
    print(f"  {'─' * 35} {'─' * 8} {'─' * 12} {'─' * 10} {'─' * 6} {'─' * 10}")
    for r in results:
        art = f"{r.artifact_count} ({', '.join(r.artifact_types[:3])})" if r.artifact_count else "—"
        err = r.error_detail[:30] if r.error_detail else "—"
        print(f"  {r.name[:35]:<35} {r.status_label:<8} {art:<12} "
              f"{r.total_seconds:>6.0f}s   {len(r.gate_approvals):<6} {err}")

    total_p = sum(r.passed for r in results)
    total_f = sum(r.failed for r in results)
    total_s = sum(r.skipped for r in results)
    print(f"\n{'─' * 70}")
    if total_f == 0:
        print(f"  ✅ ALL SCENARIOS PASSED: {total_p} passed, {total_s} skipped")
    else:
        print(f"  ❌ SOME SCENARIOS FAILED: {total_p} passed, {total_f} failed, {total_s} skipped")
        for r in results:
            if not r.ok:
                print(f"     ❌ {r.name}")
                for step in r.steps:
                    if "❌" in step:
                        print(f"        {step.strip()}")
    print(f"{'─' * 70}")
    sys.exit(0 if total_f == 0 else 1)


if __name__ == "__main__":
    main()
