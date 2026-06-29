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

BASE_URL: Final = os.environ.get("OMC_GATEWAY_URL", "http://127.0.0.1:8101")
DATABASE_URL: Final = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
OUTPUT_PATH: Final = Path(
    ".scratch/pipeline-v2/artifacts/live-v2-no-long-request-2026-06-29.json",
)
MAX_CREATE_SECONDS: Final = 2.0
MAX_RESUME_SECONDS: Final = 2.0


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
        detail = exc.read().decode("utf-8", errors="replace")
        elapsed = time.perf_counter() - started
        return exc.code, {"detail": detail}, elapsed


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


def job_rows(engine, run_id: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select job_id, kind, status, attempts, lease_owner "
                "from public.run_jobs where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def cancel_run(token: str, run_id: str) -> dict:
    status, body, elapsed = request_json("POST", f"/teaching-packs/run/{run_id}/cancel", token)
    return {"status_code": status, "elapsed_seconds": round(elapsed, 4), "body": body}


def main() -> None:
    marker = f"LIVE_V2_NO_LONG_REQUEST_{uuid4()}"
    teacher_id = f"teacher-no-long-{uuid4()}"
    token = token_for(teacher_id)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    create_body = {
        "raw_request": marker,
        "class_info": {"topic": "Fast gate timing"},
    }
    create_key = f"no-long-create-{uuid4()}"
    first_status, first_body, first_elapsed = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        create_body,
        {"Idempotency-Key": create_key},
    )
    duplicate_status, duplicate_body, duplicate_elapsed = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        create_body,
        {"Idempotency-Key": create_key},
    )
    run_id = str(first_body["run_id"])
    gate = active_gate(engine, run_id)
    resume_body = {
        "gate_id": gate["gate_id"],
        "gate_name": gate["gate_name"],
        "action": "answer",
        "response": {"subject": "Math", "grade_band": "Grade 5"},
    }
    resume_status, resume_response, resume_elapsed = request_json(
        "POST",
        f"/teaching-packs/runs/{run_id}/resume",
        token,
        resume_body,
        {"Idempotency-Key": f"no-long-resume-{uuid4()}"},
    )
    cleanup = cancel_run(token, run_id)
    jobs = job_rows(engine, run_id)
    engine.dispose()
    assertions = {
        "create_returned_202": first_status == 202,
        "create_returned_under_threshold": first_elapsed < MAX_CREATE_SECONDS,
        "duplicate_create_returned_under_threshold": duplicate_elapsed < MAX_CREATE_SECONDS,
        "duplicate_create_reused_run": duplicate_body.get("run_id") == run_id,
        "create_stopped_at_gate_without_job": first_body.get("job_id") is None,
        "clarification_gate_was_active": gate["gate_name"] == "clarification_required",
        "resume_returned_202": resume_status == 202,
        "resume_returned_under_threshold": resume_elapsed < MAX_RESUME_SECONDS,
        "resume_queued_job_instead_of_running_inline": bool(resume_response.get("job_id")),
    }
    evidence = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "surface": "/teaching-packs/*",
        "gateway": BASE_URL,
        "marker": marker,
        "scenario": "create_resume_no_long_request_timing",
        "thresholds_seconds": {
            "create": MAX_CREATE_SECONDS,
            "resume": MAX_RESUME_SECONDS,
        },
        "run_id": run_id,
        "observations": {
            "first_create": {
                "status_code": first_status,
                "elapsed_seconds": round(first_elapsed, 4),
                "body": first_body,
            },
            "duplicate_create": {
                "status_code": duplicate_status,
                "elapsed_seconds": round(duplicate_elapsed, 4),
                "body": duplicate_body,
            },
            "active_gate_before_resume": gate,
            "clarification_resume": {
                "status_code": resume_status,
                "elapsed_seconds": round(resume_elapsed, 4),
                "body": resume_response,
            },
            "jobs_after_resume": jobs,
            "cleanup": cleanup,
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
