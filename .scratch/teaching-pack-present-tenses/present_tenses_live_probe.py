from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
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
    ".scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe.json",
)
EXPORT_DIR: Final = Path(".scratch/teaching-pack-present-tenses/artifacts/live-exports")
POLL_SECONDS: Final = int(os.environ.get("OMC_PRESENT_TENSES_POLL_SECONDS", "900"))


@dataclass(frozen=True, slots=True)
class ProbeResult:
    run_id: str
    marker: str
    final_status: str
    preview_paths: list[str]
    export_paths: list[str]
    state: dict[str, object]
    evidence: dict[str, object] | None


def request_json(
    method: str,
    path: str,
    token: str | None = None,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
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
    parsed = json.loads(raw) if raw else {}
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{method} {path} returned non-object JSON")
    return parsed


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


def db_state(engine: object, run_id: str) -> dict[str, object]:
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
                "where run_id = :run_id order by sequence desc limit 20"
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


def active_gate(state: dict[str, object], gate_name: str) -> dict[str, object] | None:
    gates = state.get("gates", [])
    if not isinstance(gates, list):
        return None
    for gate in gates:
        if isinstance(gate, dict) and gate.get("gate_name") == gate_name and gate.get("status") == "active":
            return gate
    return None


def poll_until_gate_or_terminal(engine: object, run_id: str, gate_name: str) -> tuple[str, dict[str, object], dict[str, object] | None]:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        gate = active_gate(state, gate_name)
        if gate is not None:
            return "gate", state, gate
        run_rows = state.get("run", [])
        if isinstance(run_rows, list) and run_rows:
            status = run_rows[0].get("status") if isinstance(run_rows[0], dict) else None
            if isinstance(status, str) and status.lower() in {"completed", "failed", "cancelled"}:
                return "terminal", state, None
        time.sleep(5)
    return "timeout", db_state(engine, run_id), None


def poll_until_terminal(engine: object, run_id: str) -> tuple[str, dict[str, object]]:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        run_rows = state.get("run", [])
        if isinstance(run_rows, list) and run_rows:
            status = run_rows[0].get("status") if isinstance(run_rows[0], dict) else None
            if isinstance(status, str) and status.lower() in {"completed", "failed", "cancelled"}:
                return status.lower(), state
        time.sleep(5)
    return "timeout", db_state(engine, run_id)


def approve_gate(token: str, run_id: str, gate: dict[str, object], response: dict[str, object] | None = None) -> dict[str, object]:
    gate_id = str(gate["gate_id"])
    gate_name = str(gate["gate_name"])
    return request_json(
        "POST",
        f"/teaching-packs/runs/{run_id}/resume",
        token,
        {
            "gate_id": gate_id,
            "gate_name": gate_name,
            "action": "approve",
            "response": response or {},
        },
        headers={"Idempotency-Key": f"resume-{gate_id}-{uuid4()}"},
    )


def assert_preview_invariants(html: str) -> None:
    lowered = html.lower()
    if "<!doctype html" not in lowered:
        raise AssertionError("preview missing doctype")
    if "oh-my-class" not in lowered:
        raise AssertionError("preview missing brand")
    if "http://" in lowered or "https://" in lowered:
        raise AssertionError("preview contains external URL")
    for token in ["answer key", "correct answer", "đáp án", "answer:", "correct:", "solution:"]:
        if token in lowered:
            raise AssertionError(f"preview leaks answer marker {token!r}")


def save_preview(run_id: str, snapshot_id: str, html: str) -> str:
    export_dir = EXPORT_DIR / run_id
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"{snapshot_id}-student.html"
    path.write_text(html, encoding="utf-8")
    return str(path)


def snapshot_ids_from(gate: dict[str, object]) -> list[str]:
    payload = gate.get("payload", {})
    if not isinstance(payload, dict):
        return []
    values = payload.get("snapshot_ids", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def run_probe() -> ProbeResult:
    marker = str(uuid4())
    login = request_json("POST", "/auth/login", body={"username": "teacher1", "password": "dev"})
    token = str(login["access_token"])
    engine = create_engine(DATABASE_URL)
    raw_request = (
        f"PRESENT_TENSES_INVERSE_THINKING_LIVE {marker}: "
        "Create a B2 English teaching pack for Vietnamese learners on Present Tenses. "
        "Use inverse thinking: start from wrong tense traps, explain what meaning breaks, "
        "cover Present Simple, Present Continuous, Present Perfect Simple, Present Perfect Continuous, "
        "and stative verbs like think/have. Include lesson, worksheet, quiz, and recap. "
        "No student PII, no external assets, teacher-only answer key."
    )
    accepted = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {"raw_request": raw_request, "class_info": {"grade": 10, "subject": "English", "student_count": 18, "language": "vi"}},
        headers={"Idempotency-Key": f"present-tenses-{marker}"},
    )
    run_id = str(accepted["run_id"])

    contract_status, contract_state, contract_gate = poll_until_gate_or_terminal(engine, run_id, "contract_confirmation")
    if contract_status != "gate" or contract_gate is None:
        return ProbeResult(run_id, marker, f"missing_contract_gate:{contract_status}", [], [], contract_state, None)
    approve_gate(token, run_id, contract_gate)

    content_status, content_state, content_gate = poll_until_gate_or_terminal(engine, run_id, "content_approval")
    if content_status != "gate" or content_gate is None:
        return ProbeResult(run_id, marker, f"missing_content_gate:{content_status}", [], [], content_state, None)

    preview_paths = []
    snapshot_ids = snapshot_ids_from(content_gate)
    for snapshot_id in snapshot_ids:
        quoted = urllib.parse.quote(snapshot_id, safe="")
        html = request_text(f"/teaching-packs/runs/{run_id}/snapshots/{quoted}/preview?view=student", token)
        assert_preview_invariants(html)
        preview_paths.append(save_preview(run_id, snapshot_id, html))

    request_json("POST", f"/teaching-packs/runs/{run_id}/approved-snapshots", token, {"snapshot_ids": snapshot_ids})
    approve_gate(token, run_id, content_gate, {"approved_snapshot_ids": snapshot_ids})
    final_status, final_state = poll_until_terminal(engine, run_id)
    evidence = None
    if final_status == "completed":
        evidence = request_json("GET", f"/teaching-packs/run/{run_id}/evidence", token)
    export_paths = []
    if evidence is not None:
        exported = evidence.get("exported_files", [])
        if isinstance(exported, list):
            export_paths = [str(path) for path in exported]
    return ProbeResult(run_id, marker, final_status, preview_paths, export_paths, final_state, evidence)


def main() -> int:
    result = run_probe()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": result.run_id,
        "marker": result.marker,
        "final_status": result.final_status,
        "preview_paths": result.preview_paths,
        "export_paths": result.export_paths,
        "state": result.state,
        "evidence": result.evidence,
    }
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(OUTPUT_PATH)
    print(json.dumps(data, indent=2, default=str))
    return 0 if result.final_status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
