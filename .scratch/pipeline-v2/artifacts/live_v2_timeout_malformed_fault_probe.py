from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final
from uuid import uuid4

import anyio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from services.gateway.auth.jwt_handler import create_access_token
from services.gateway.auth.models import Role, User
from services.gateway.teaching_pack_executor import (
    TeachingPackExecutor,
    TeachingPackFailureRecorder,
)
from services.gateway.teaching_pack_job_store import TeachingPackJobStore
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_worker import TeachingPackWorker, TeachingPackWorkerConfig

if TYPE_CHECKING:
    from langgraph.types import Command

    from packages.agents.teaching_pack.graph import LangGraphRunnableConfig
    from services.gateway.teaching_pack_types import JsonObject

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
    ".scratch/pipeline-v2/artifacts/live-v2-timeout-malformed-fault-2026-06-29.json",
)


@dataclass(slots=True)
class InlineTaskGroup:
    def start_soon(self, func, *args) -> None:
        _ = (func, args)


class TimeoutGraph:
    async def ainvoke(
        self,
        input_data: "JsonObject | Command[tuple[()]]",
        *,
        config: "LangGraphRunnableConfig",
    ) -> "JsonObject":
        _ = (input_data, config)
        raise TimeoutError("fault-injected provider timeout")


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


def force_claim_priority(engine, job_id: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "update public.run_jobs "
                "set status = 'pending', eligible_at = null, "
                "created_at = '2000-01-01T00:00:00Z' "
                "where job_id = :job_id"
            ),
            {"job_id": job_id},
        )


def job_rows(engine, run_id: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select job_id, kind, status, attempts, lease_owner, payload "
                "from public.run_jobs where run_id = :run_id order by created_at"
            ),
            {"run_id": run_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def run_row(engine, run_id: str) -> dict:
    with engine.connect() as connection:
        row = connection.execute(
            text("select run_id, teacher_id, status, raw_request from public.runs where run_id = :run_id"),
            {"run_id": run_id},
        ).mappings().one()
    return dict(row)


def event_rows(engine, run_id: str) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "select sequence, event_name, payload from public.run_events "
                "where run_id = :run_id order by sequence"
            ),
            {"run_id": run_id},
        ).mappings().all()
    return [dict(row) for row in rows]


async def run_faulting_worker_once() -> bool:
    engine = create_async_engine(DATABASE_URL_ASYNC, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        store = TeachingPackRunStore(session)
        executor = TeachingPackExecutor(
            TimeoutGraph(),
            InlineTaskGroup(),
            TeachingPackFailureRecorder(store),
        )
        worker = TeachingPackWorker(
            TeachingPackJobStore(session),
            executor,
            TeachingPackWorkerConfig(
                worker_id=f"fault-worker-{uuid4()}",
                lease_seconds=30,
                idle_sleep_seconds=0,
            ),
        )
        did_work = await worker.run_one()
        await session.commit()
    await engine.dispose()
    return did_work


def cleanup_run(token: str, run_id: str) -> dict:
    status, body, elapsed = request_json("POST", f"/teaching-packs/run/{run_id}/cancel", token)
    return {"status_code": status, "elapsed_seconds": round(elapsed, 4), "body": body}


def main() -> None:
    marker = f"LIVE_V2_TIMEOUT_MALFORMED_FAULT_{uuid4()}"
    teacher_id = f"teacher-fault-{uuid4()}"
    token = token_for(teacher_id)
    engine = create_engine(DATABASE_URL_SYNC, pool_pre_ping=True)
    create_status, create_body, create_elapsed = request_json(
        "POST",
        "/teaching-packs/runs",
        token,
        {
            "raw_request": f"{marker} Grade 5 math lesson about equivalent fractions.",
            "class_info": {
                "grade": 5,
                "subject": "math",
                "topic": "Equivalent fractions",
            },
        },
        {"Idempotency-Key": f"fault-create-{uuid4()}"},
    )
    run_id = str(create_body["run_id"])
    job_id = str(create_body["job_id"])
    force_claim_priority(engine, job_id)
    did_work = anyio.run(run_faulting_worker_once)
    run_after_fault = run_row(engine, run_id)
    jobs_after_fault = job_rows(engine, run_id)
    events_after_fault = event_rows(engine, run_id)
    cleanup = cleanup_run(token, run_id)
    engine.dispose()
    failed_events = [event for event in events_after_fault if event["event_name"] == "teaching_pack.run.failed"]
    assertions = {
        "public_create_returned_start_job": create_status == 202 and create_body.get("job_id") == job_id,
        "faulting_worker_claimed_work": did_work is True,
        "run_failed_closed": run_after_fault["status"] == "FAILED",
        "job_failed_closed": any(job["job_id"] == job_id and job["status"] == "failed" for job in jobs_after_fault),
        "failure_event_persisted": len(failed_events) == 1,
        "timeout_summary_redacted_and_persisted": bool(failed_events) and "TimeoutError: fault-injected provider timeout" in str(failed_events[0]["payload"]),
        "cleanup_succeeded_or_already_terminal": cleanup["status_code"] in {200, 409},
    }
    evidence = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "surface": "/teaching-packs/* public create + TeachingPackWorker/TeachingPackExecutor",
        "gateway": BASE_URL,
        "marker": marker,
        "scenario": "fault_injected_timeout_fail_closed_public_job",
        "run_id": run_id,
        "job_id": job_id,
        "observations": {
            "create": {
                "status_code": create_status,
                "elapsed_seconds": round(create_elapsed, 4),
                "body": create_body,
            },
            "worker_did_work": did_work,
            "run_after_fault": run_after_fault,
            "jobs_after_fault": jobs_after_fault,
            "events_after_fault": events_after_fault,
            "cleanup": cleanup,
        },
        "paired_deterministic_malformed_json_evidence": {
            "test_file": "packages/agents/tests/sub_agents/test_content_creator_per_artifact.py",
            "cases": [
                "test_success_after_retry_returns_correct_artifact",
                "test_all_retries_exhausted_raises_value_error",
                "test_timeout_exception_retries_and_recovers_for_target_artifact"
            ]
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
