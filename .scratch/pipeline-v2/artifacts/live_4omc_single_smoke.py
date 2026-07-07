# /// script
# requires-python = ">=3.12"
# dependencies = ["sqlalchemy>=2.0", "psycopg[binary]>=3.2"]
# ///
# ─── How to run ───
# JWT_SECRET=dev-live-4omc-secret-not-production OMC_GATEWAY_URL=http://127.0.0.1:8103 uv run .scratch/pipeline-v2/artifacts/live_4omc_single_smoke.py

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

BASE_URL: Final = os.environ.get("OMC_GATEWAY_URL", "http://127.0.0.1:8103")
DATABASE_URL: Final = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
OUTPUT_PATH: Final = Path(".scratch/pipeline-v2/artifacts/live-4omc-slide-deck-smoke-2026-07-07.json")
POLL_SECONDS: Final = 600
TEACHER_PROMPT: Final = (
    "Generate a slide deck for Grade 5 English ESL food vocabulary. "
    "Include teachable slide titles, student-safe interactions, and teacher-only answers."
)
EXPECTED_TOPIC: Final = "Grade 5 English ESL food vocabulary"


class JsonMap(TypedDict, total=False):
    run_id: str
    gate_id: str
    gate_name: str
    action: str
    response: dict[str, str]


@dataclass(frozen=True, slots=True)
class HttpResult:
    status: int
    body: dict[str, object]


def request_json(method: str, path: str, token: str | None = None, body: dict[str, object] | None = None) -> dict[str, object]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
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
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8")


def db_state(engine: Engine, run_id: str) -> dict[str, object]:
    queries: Final = {
        "run": "select run_id,status from public.runs where run_id=:run_id",
        "gates": "select gate_id,gate_name,status,payload from public.gate_interrupts where run_id=:run_id order by created_at",
        "snapshots": "select snapshot_id,artifact_id,artifact_type,standalone_valid,length(student_rendered_html) as student_html_len from public.artifact_snapshots where run_id=:run_id order by created_at",
        "events": "select sequence,event_name,stage,payload from public.run_events where run_id=:run_id order by sequence",
    }
    state: dict[str, object] = {}
    with engine.connect() as connection:
        for name, sql in queries.items():
            rows = connection.execute(text(sql), {"run_id": run_id}).mappings().all()
            state[name] = [dict(row) for row in rows]
    return state


def active_gate(state: dict[str, object], gate_name: str) -> dict[str, object] | None:
    gates = state["gates"]
    if not isinstance(gates, list):
        return None
    for gate in gates:
        if isinstance(gate, dict) and gate.get("gate_name") == gate_name and gate.get("status") == "active":
            return gate
    return None


def poll_gate(engine: Engine, run_id: str, gate_name: str) -> dict[str, object]:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        gate = active_gate(state, gate_name)
        if gate is not None:
            return gate
        time.sleep(3)
    raise RuntimeError(f"timeout waiting for {gate_name}: {db_state(engine, run_id)}")


def poll_terminal(engine: Engine, run_id: str) -> str:
    deadline = time.monotonic() + POLL_SECONDS
    while time.monotonic() < deadline:
        state = db_state(engine, run_id)
        run_rows = state["run"]
        if isinstance(run_rows, list) and run_rows:
            status = str(run_rows[0]["status"])
            if status in {"COMPLETED", "FAILED", "CANCELLED"}:
                return status
        time.sleep(3)
    return "TIMEOUT"


def approve_gate(token: str, run_id: str, gate: dict[str, object], response: dict[str, object] | None = None) -> dict[str, object]:
    return request_json(
        "POST",
        f"/teaching-packs/runs/{run_id}/resume",
        token,
        {
            "gate_id": str(gate["gate_id"]),
            "gate_name": str(gate["gate_name"]),
            "action": "approve",
            "response": response or {},
        },
    )


def assert_preview(html: str) -> None:
    lowered = html.lower()
    if "<!doctype html" not in lowered:
        raise AssertionError("missing doctype")
    if "oh-my-class" not in lowered:
        raise AssertionError("missing brand")
    if "http://" in lowered or "https://" in lowered:
        raise AssertionError("external asset leak")
    for marker in ("answer key", "correct answer", "đáp án", "answer:", "correct:", "solution:"):
        if marker in lowered:
            raise AssertionError(f"answer marker leaked: {marker}")
    for marker in ("slide-deck", "slide-card", "slide 1"):
        if marker not in lowered:
            raise AssertionError(f"missing slide-deck marker: {marker}")
    if lowered.count("slide-card") < 6:
        raise AssertionError("slide deck is too thin: expected at least 6 rendered slide cards")
    for marker in ("learning goal", "key vocabulary", "worked example", "guided practice", "exit ticket"):
        if marker not in lowered:
            raise AssertionError(f"missing teaching sequence marker: {marker}")
    if EXPECTED_TOPIC.lower() not in lowered:
        raise AssertionError(f"missing expected topic: {EXPECTED_TOPIC}")
    for marker in (
        "live_4omc_slide_deck_smoke",
        "generate a slide deck",
        "include teachable slide titles",
        "teacher-only answers",
    ):
        if marker in lowered:
            raise AssertionError(f"raw prompt leaked: {marker}")


def assert_contract_gate(gate: dict[str, object]) -> None:
    payload = gate["payload"]
    if not isinstance(payload, dict):
        raise RuntimeError("contract gate payload is not a dict")
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        raise RuntimeError(f"contract gate has no contract: {payload}")
    artifact_types = contract.get("artifact_types")
    if artifact_types != ["slide_deck"]:
        raise AssertionError(f"expected slide_deck contract, got: {artifact_types}")


def assert_slide_deck_snapshots(state: dict[str, object], snapshot_ids: list[object]) -> None:
    snapshots = state["snapshots"]
    if not isinstance(snapshots, list):
        raise RuntimeError(f"snapshot state is not a list: {snapshots}")
    by_id = {str(snapshot["snapshot_id"]): snapshot for snapshot in snapshots if isinstance(snapshot, dict)}
    for snapshot_id in snapshot_ids:
        snapshot = by_id.get(str(snapshot_id))
        if snapshot is None:
            raise AssertionError(f"missing snapshot row for {snapshot_id}")
        if snapshot.get("artifact_type") != "slide_deck":
            raise AssertionError(f"expected slide_deck snapshot, got: {snapshot}")


def main() -> int:
    token = str(request_json("POST", "/auth/login", body={"username": "teacher1", "password": "dev"})["access_token"])
    engine = create_engine(DATABASE_URL)
    accepted = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {
            "raw_request": TEACHER_PROMPT,
            "class_info": {"grade": 5, "subject": "English", "student_count": 28, "language": "en"},
        },
    )
    run_id = str(accepted["run_id"])
    contract_gate = poll_gate(engine, run_id, "contract_confirmation")
    assert_contract_gate(contract_gate)
    approve_gate(token, run_id, contract_gate)
    content_gate = poll_gate(engine, run_id, "content_approval")
    payload = content_gate["payload"]
    if not isinstance(payload, dict):
        raise RuntimeError("content gate payload is not a dict")
    snapshot_ids = payload.get("snapshot_ids")
    if not isinstance(snapshot_ids, list) or not snapshot_ids:
        raise RuntimeError(f"content approval has no snapshots: {payload}")
    assert_slide_deck_snapshots(db_state(engine, run_id), snapshot_ids)
    preview_checks: list[dict[str, object]] = []
    for snapshot_id in snapshot_ids:
        html = request_text(f"/teaching-packs/runs/{run_id}/snapshots/{snapshot_id}/preview?view=student", token)
        assert_preview(html)
        preview_checks.append({"snapshot_id": snapshot_id, "student_html_len": len(html)})
    request_json("POST", f"/teaching-packs/runs/{run_id}/approved-snapshots", token, {"snapshot_ids": snapshot_ids})
    approve_gate(token, run_id, content_gate, {"approved_snapshot_ids": snapshot_ids})
    final_status = poll_terminal(engine, run_id)
    evidence = {
        "run_id": run_id,
        "teacher_prompt": TEACHER_PROMPT,
        "expected_topic": EXPECTED_TOPIC,
        "accepted": accepted,
        "snapshot_ids": snapshot_ids,
        "preview_checks": preview_checks,
        "final_status": final_status,
        "state": db_state(engine, run_id),
    }
    OUTPUT_PATH.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(json.dumps(evidence, indent=2, default=str))
    return 0 if final_status == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
