from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Final
from uuid import uuid4

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User

BASE_URL: Final = os.environ.get("OMC_GATEWAY_URL", "http://127.0.0.1:8102")
DATABASE_URL: Final = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
OUTPUT_PATH: Final = Path(
    ".scratch/pipeline-v2/artifacts/live-v2-langfuse-unavailable-2026-06-29.json",
)


def token_for(teacher_id: str) -> str:
    token = create_access_token(User(
        user_id=teacher_id,
        username=teacher_id,
        role=Role.TEACHER,
        organization_id="org-live-v2",
        class_id="class-live-v2",
    ))
    return token.access_token


def request_json(
    method: str,
    path: str,
    token: str,
    body: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict, float]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    if headers is not None:
        req_headers.update(headers)
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=req_headers,
        method=method,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            elapsed = time.perf_counter() - started
            return response.status, json.loads(raw) if raw else {}, elapsed
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - started
        raw = exc.read().decode("utf-8", errors="replace")
        return exc.code, {"detail": raw}, elapsed


def active_gate(engine, run_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "select gate_id, gate_name, status, payload "
                "from public.gate_interrupts where run_id = :run_id and status = 'active' "
                "order by created_at desc limit 1"
            ),
            {"run_id": run_id},
        ).mappings().one()
    return dict(row)


def run_row(engine, run_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text("select run_id, teacher_id, status from public.runs where run_id = :run_id"),
            {"run_id": run_id},
        ).mappings().one()
    return dict(row)


def main() -> None:
    marker = f"LIVE_V2_LANGFUSE_UNAVAILABLE_{uuid4()}"
    teacher_id = f"teacher-langfuse-{uuid4()}"
    token = token_for(teacher_id)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    status_code, create_body, create_elapsed = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {"raw_request": marker, "class_info": {"topic": "Langfuse unavailable mode"}},
        {"Idempotency-Key": f"langfuse-unavailable-{uuid4()}"},
    )
    run_id = str(create_body["run_id"])
    gate = active_gate(engine, run_id)
    persisted_run = run_row(engine, run_id)
    cancel_status, cancel_body, cancel_elapsed = request_json(
        "POST",
        f"/teaching-packs/run/{run_id}/cancel",
        token,
    )
    engine.dispose()
    assertions = {
        "gateway_with_unreachable_langfuse_accepted_public_create": status_code == 202,
        "run_persisted_for_teacher": persisted_run["teacher_id"] == teacher_id,
        "run_reached_clarification_gate": gate["gate_name"] == "clarification_required",
        "run_status_awaiting_approval": create_body.get("status") == "awaiting_approval",
        "create_did_not_queue_start_job_before_gate": create_body.get("job_id") is None,
        "cleanup_cancel_succeeded": cancel_status == 200,
    }
    evidence = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "surface": "/teaching-packs/*",
        "gateway": BASE_URL,
        "langfuse_env": {
            "LANGFUSE_PUBLIC_KEY": "configured-test-key",
            "LANGFUSE_SECRET_KEY": "configured-test-secret",
            "LANGFUSE_HOST": "http://127.0.0.1:9",
        },
        "marker": marker,
        "scenario": "langfuse_unavailable_public_create_does_not_block_run",
        "run_id": run_id,
        "observations": {
            "create": {
                "status_code": status_code,
                "elapsed_seconds": round(create_elapsed, 4),
                "body": create_body,
            },
            "active_gate": gate,
            "persisted_run": persisted_run,
            "cleanup": {
                "status_code": cancel_status,
                "elapsed_seconds": round(cancel_elapsed, 4),
                "body": cancel_body,
            },
        },
        "assertions": assertions,
        "passed": all(assertions.values()),
    }
    OUTPUT_PATH.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "passed": evidence["passed"], "run_id": run_id}, indent=2))
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
