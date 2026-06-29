# /// script
# requires-python = ">=3.12"
# ///
# ─── How to run ───
# uv run .scratch/pipeline-v2/artifacts/live_pipeline_v2_probe.py

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from uuid import uuid4

from sqlalchemy import create_engine, text

BASE_URL: Final = os.environ.get("OMC_GATEWAY_URL", "http://127.0.0.1:8101")
DATABASE_URL: Final = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
OUTPUT_PATH: Final = Path(
    ".scratch/pipeline-v2/artifacts/live-v2-matrix-after-renderer-leak-fix-2026-06-28.json",
)
POLL_SECONDS: Final = 900


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    raw_request: str
    class_info: dict[str, str | int]


SCENARIOS: Final = [
    Scenario(
        name="esl",
        raw_request=(
            "LIVE_V2_ESL_RENDER_FIX {marker}: Grade 5 English ESL lesson on food vocabulary, "
            "include lesson and quiz, clear teacher-only answer key, no answer leakage in student preview."
        ),
        class_info={"grade": 5, "subject": "English", "student_count": 28, "language": "en"},
    ),
    Scenario(
        name="science",
        raw_request=(
            "LIVE_V2_SCIENCE_RENDER_FIX {marker}: Grade 6 science teaching pack on water cycle, "
            "include lesson, recap, quiz, citations or source notes where factual claims need them, "
            "and teacher-only answer key."
        ),
        class_info={"grade": 6, "subject": "Science", "student_count": 32, "language": "en"},
    ),
]


def request_json(
    method: str,
    path: str,
    token: str | None = None,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json"}
    if token is not None:
        req_headers["Authorization"] = f"Bearer {token}"
    if headers is not None:
        req_headers.update(headers)
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=req_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: {exc.code} {detail}") from exc
    return json.loads(raw) if raw else {}


def request_text(path: str, token: str) -> str:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed: {exc.code} {detail}") from exc


def db_state(engine, run_id: str) -> dict:
    with engine.connect() as connection:
        run = connection.execute(
            text("select run_id, teacher_id, status, updated_at from public.runs where run_id = :run_id"),
            {"run_id": run_id},
        ).mappings().all()
        jobs = connection.execute(
            text(
                "select job_id, kind, status, attempts, lease_owner, lease_expires_at "
                "from public.run_jobs where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
        gates = connection.execute(
            text(
                "select gate_id, gate_name, status, payload from public.gate_interrupts "
                "where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
        snaps = connection.execute(
            text(
                "select snapshot_id, artifact_id, artifact_type, standalone_valid, approved_at, "
                "length(student_rendered_html) as student_html_len from public.artifact_snapshots "
                "where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
        events_tail = connection.execute(
            text(
                "select sequence, event_name, payload from public.run_events "
                "where run_id = :run_id order by sequence desc limit 10"
            ),
            {"run_id": run_id},
        ).mappings().all()
        history = connection.execute(
            text(
                "select status, stage, reason from public.run_status_history "
                "where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
    return {
        "run": [dict(row) for row in run],
        "jobs": [dict(row) for row in jobs],
        "gates": [dict(row) for row in gates],
        "snaps": [dict(row) for row in snaps],
        "events_tail": [dict(row) for row in reversed(events_tail)],
        "history": [dict(row) for row in history],
    }


def active_gate(state: dict, gate_name: str) -> dict | None:
    for gate in state["gates"]:
        if gate["gate_name"] == gate_name and gate["status"] == "active":
            return gate
    return None


def assert_preview_invariants(html: str) -> None:
    lowered = html.lower()
    if "<!doctype html" not in lowered:
        raise AssertionError("preview missing doctype")
    if "oh-my-class" not in lowered:
        raise AssertionError("preview missing brand")
    if "http://" in lowered or "https://" in lowered:
        raise AssertionError("preview contains external URL")
    forbidden = ["answer key", "correct answer", "đáp án", "answer:", "correct:", "solution:"]
    for token in forbidden:
        if token in lowered:
            raise AssertionError(f"preview leaks answer marker {token!r}")


def poll_until_gate_or_terminal(engine, run_id: str, gate_name: str) -> tuple[str, dict, dict | None]:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        gate = active_gate(state, gate_name)
        if gate is not None:
            return "gate", state, gate
        run_rows = state["run"]
        if run_rows and run_rows[0]["status"] in {"completed", "failed", "cancelled"}:
            return "terminal", state, None
        time.sleep(5)
    return "timeout", db_state(engine, run_id), None


def poll_until_terminal(engine, run_id: str) -> tuple[str, dict]:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        run_rows = state["run"]
        if run_rows and run_rows[0]["status"] in {"completed", "failed", "cancelled"}:
            return run_rows[0]["status"], state
        time.sleep(5)
    return "timeout", db_state(engine, run_id)


def approve_gate(token: str, run_id: str, gate: dict, response: dict | None = None) -> dict:
    return request_json(
        "POST",
        f"/teaching-packs/runs/{run_id}/resume",
        token,
        {
            "gate_id": gate["gate_id"],
            "gate_name": gate["gate_name"],
            "action": "approve",
            "response": response or {},
        },
        headers={"Idempotency-Key": f"resume-{gate['gate_id']}-{uuid4()}"},
    )


def run_scenario(engine, token: str, scenario: Scenario) -> dict:
    marker = str(uuid4())
    raw_request = scenario.raw_request.format(marker=marker)
    accepted = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {"raw_request": raw_request, "class_info": scenario.class_info},
        headers={"Idempotency-Key": f"live-{scenario.name}-{marker}"},
    )
    run_id = accepted["run_id"]
    first_status, first_state, first_gate = poll_until_gate_or_terminal(engine, run_id, "contract_confirmation")
    if first_status != "gate" or first_gate is None:
        return {"name": scenario.name, "marker": marker, "run_id": run_id, "error": "contract_gate_not_reached", "state": first_state}
    contract_resume = approve_gate(token, run_id, first_gate)
    content_status, content_state, content_gate = poll_until_gate_or_terminal(engine, run_id, "content_approval")
    if content_status != "gate" or content_gate is None:
        return {
            "name": scenario.name,
            "marker": marker,
            "run_id": run_id,
            "contract_resume": contract_resume,
            "error": "content_gate_not_reached",
            "state": content_state,
        }
    snapshot_ids = list(content_gate["payload"].get("snapshot_ids", []))
    preview_checks = []
    for snapshot_id in snapshot_ids:
        metadata = request_json("GET", f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}", token)
        html = request_text(f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/preview?view=student", token)
        assert_preview_invariants(html)
        preview_checks.append({"snapshot_id": snapshot_id, "metadata": metadata, "student_html_len": len(html)})
    approved = request_json(
        "POST",
        f"/teaching-packs/runs/{run_id}/approved-snapshots",
        token,
        {"snapshot_ids": snapshot_ids},
    )
    content_resume = approve_gate(token, run_id, content_gate, {"approved_snapshot_ids": snapshot_ids})
    final_status, final_state = poll_until_terminal(engine, run_id)
    evidence = None
    if final_status == "completed":
        evidence = request_json("GET", f"/teaching-packs/run/{run_id}/evidence", token)
    return {
        "name": scenario.name,
        "marker": marker,
        "run_id": run_id,
        "accepted": accepted,
        "contract_resume": contract_resume,
        "preview_checks": preview_checks,
        "approved": approved,
        "content_resume": content_resume,
        "final_status": final_status,
        "final_state": final_state,
        "evidence": evidence,
    }


def main() -> int:
    token_response = request_json("POST", "/auth/login", body={"username": "teacher1", "password": "dev"})
    token = token_response["access_token"]
    engine = create_engine(DATABASE_URL)
    results = []
    for scenario in SCENARIOS:
        try:
            results.append(run_scenario(engine, token, scenario))
        except Exception as exc:
            results.append({"name": scenario.name, "error": type(exc).__name__, "message": str(exc)})
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(OUTPUT_PATH)
    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
