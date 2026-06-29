from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final
from uuid import uuid4

import anyio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User
from services.gateway.teaching_pack_job_store import TeachingPackJobStore

BASE_URL: Final = os.environ.get("OMC_GATEWAY_URL", "http://127.0.0.1:8101")
DATABASE_URL_SYNC: Final = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
DATABASE_URL_ASYNC: Final = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
)
OUTPUT_PATH: Final = Path(
    ".scratch/pipeline-v2/artifacts/live-v2-worker-lease-2026-06-29.json",
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


def job_row(engine, job_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "select job_id, run_id, kind, status, attempts, lease_owner, lease_expires_at "
                "from public.run_jobs where job_id = :job_id"
            ),
            {"job_id": job_id},
        ).mappings().one()
    return dict(row)


def insert_simulated_running_job(engine, run_id: str, job_id: str) -> dict:
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    with engine.begin() as connection:
        connection.execute(
            text(
                "insert into public.run_jobs "
                "(job_id, run_id, kind, status, idempotency_key, payload, attempts, lease_owner, lease_expires_at) "
                "values (:job_id, :run_id, 'start', 'running', :idempotency_key, :payload, "
                "1, :owner, :expires_at)"
            ),
            {
                "job_id": job_id,
                "run_id": run_id,
                "idempotency_key": f"lease-recovery-{job_id}",
                "payload": json.dumps({"source": "live-worker-lease-proof"}),
                "owner": "simulated-crashed-worker",
                "expires_at": expires_at,
            },
        )
    return job_row(engine, job_id)


async def reclaim_expired_job(now: datetime) -> dict | None:
    engine = create_async_engine(DATABASE_URL_ASYNC, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        claimed = await TeachingPackJobStore(session).claim_next(
            lease_owner="simulated-restarted-worker",
            lease_seconds=30,
            now=now,
        )
        await session.commit()
    await engine.dispose()
    if claimed is None:
        return None
    return {
        "job_id": claimed.job_id,
        "run_id": claimed.run_id,
        "kind": claimed.kind.value,
        "status": claimed.status.value,
        "attempts": claimed.attempts,
    }


def main() -> None:
    marker = f"LIVE_V2_WORKER_LEASE_{uuid4()}"
    teacher_id = f"teacher-lease-{uuid4()}"
    token = token_for(teacher_id)
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    create_status, create_body, create_elapsed = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {
            "raw_request": marker,
            "class_info": {
                "topic": "Lease recovery",
            },
        },
        {"Idempotency-Key": f"worker-lease-{uuid4()}"},
    )
    run_id = str(create_body["run_id"])
    job_id = f"job-lease-proof-{uuid4()}"
    before = insert_simulated_running_job(engine, run_id, job_id)
    simulated_now = before["lease_expires_at"] + timedelta(seconds=1)
    reclaimed = anyio.run(reclaim_expired_job, simulated_now)
    after = job_row(engine, job_id)
    cancel_status, cancel_body, cancel_elapsed = request_json(
        "POST",
        f"/teaching-packs/run/{run_id}/cancel",
        token,
    )
    engine.dispose()
    assertions = {
        "public_create_reached_gate_without_start_job": create_status == 202 and create_body.get("job_id") is None,
        "lease_simulated_as_running": before["status"] == "running" and before["lease_owner"] == "simulated-crashed-worker",
        "expired_job_reclaimed": reclaimed is not None and reclaimed["job_id"] == job_id,
        "reclaim_incremented_attempts": after["attempts"] == before["attempts"] + 1,
        "reclaim_assigned_restart_worker": after["lease_owner"] == "simulated-restarted-worker",
        "cleanup_cancel_succeeded": cancel_status == 200,
    }
    evidence = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "surface": "/teaching-packs/*",
        "gateway": BASE_URL,
        "marker": marker,
        "scenario": "public_run_job_simulated_expired_lease_reclaim",
        "run_id": run_id,
        "job_id": job_id,
        "observations": {
            "create": {
                "status_code": create_status,
                "elapsed_seconds": round(create_elapsed, 4),
                "body": create_body,
            },
            "simulated_reclaim_now": simulated_now,
            "job_before_reclaim": before,
            "reclaimed_job": reclaimed,
            "job_after_reclaim": after,
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
    print(json.dumps({"output": str(OUTPUT_PATH), "passed": evidence["passed"], "run_id": run_id, "job_id": job_id}, indent=2))
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
