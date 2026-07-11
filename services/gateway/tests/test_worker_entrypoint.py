"""#119 (OPS-06 -- standalone worker entrypoint slice): the worker loop runs
correctly independent of any FastAPI app, against the real job queue.

Not covered here (see `worker_entrypoint.py`'s module docstring for the
acknowledged gap): the K8s Deployment manifest, queue-depth autoscaling, and
the 5,000-packs/day load test -- those need a real cluster this environment
can't stand up. This test proves the code-level scope item: a process that
builds its own runtime and claims/executes/drains against the real Postgres
queue without starting the FastAPI app.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

import anyio
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base, Run
from services.gateway.teaching_pack_executor import TeachingPackResumeJob, TeachingPackStartJob
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJobKind, RunJobStatus
from services.gateway.teaching_pack_runtime import build_teaching_pack_runtime
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.worker_entrypoint import run_standalone_worker, worker_id

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@dataclass(slots=True)
class RecordingExecutor:
    started: list[str] = field(default_factory=list)

    async def run_start_job(self, job: TeachingPackStartJob) -> None:
        self.started.append(job.run_id)

    async def run_resume_job(self, job: TeachingPackResumeJob) -> None:
        self.started.append(job.run_id)


@pytest.fixture
async def session_factory():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _connection: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack run_jobs table is not present")
    async with factory() as session:
        await session.execute(delete(Run).where(Run.run_id.like("test-%")))
        await session.commit()
    yield factory
    async with factory() as session:
        await session.execute(delete(Run).where(Run.run_id.like("test-%")))
        await session.commit()
    await engine.dispose()


async def _create_run(session) -> RunId:
    run_id = RunId(f"test-worker-entrypoint-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-entrypoint"),
        raw_request="Build a lesson via the standalone worker entrypoint",
        class_info={"grade": 5},
    ))
    await session.flush()
    return run_id


async def _enqueue_job(session, run_id: RunId) -> str:
    idempotency_key = f"idem-{uuid4()}"
    await TeachingPackJobStore(session).enqueue(RunJobCreate(
        job_id=f"job-{uuid4()}",
        run_id=run_id,
        kind=RunJobKind.START,
        idempotency_key=idempotency_key,
        payload={"initial_state": {"run_id": run_id}},
    ))
    return idempotency_key


def test_worker_id_is_stable_and_process_specific(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POD_NAME", raising=False)
    monkeypatch.delenv("HOSTNAME", raising=False)

    assert worker_id() == worker_id()

    monkeypatch.setenv("POD_NAME", "teaching-pack-worker-7")
    assert worker_id() == "teaching-pack-worker-7"


async def test_standalone_worker_claims_and_executes_a_real_job_then_drains(session_factory) -> None:
    from contextlib import AsyncExitStack

    async with session_factory() as session:
        run_id = await _create_run(session)
        idempotency_key = await _enqueue_job(session, run_id)
        await session.commit()

    async with AsyncExitStack() as stack:
        runtime = await build_teaching_pack_runtime(
            environment="development", database_url=DATABASE_URL, exit_stack=stack,
        )
        executor = RecordingExecutor()
        shutdown_event = anyio.Event()

        # `run_standalone_worker` loops until `shutdown_event` is set -- run
        # it in the background, wait for the one enqueued job to actually be
        # claimed and executed, then signal shutdown (the graceful-drain path
        # #119 asks for) and confirm the loop exits promptly.
        async def _run() -> None:
            await run_standalone_worker(
                runtime,
                shutdown_event=shutdown_event,
                executor_factory_override=lambda _session: executor,
            )

        with anyio.fail_after(5):
            async with anyio.create_task_group() as task_group:
                task_group.start_soon(_run)
                while not executor.started:
                    await anyio.sleep(0.01)
                shutdown_event.set()

    assert executor.started == [run_id]

    async with session_factory() as session:
        job = await TeachingPackJobStore(session).find_by_idempotency_key(idempotency_key)
        assert job is not None
        assert job.status == RunJobStatus.COMPLETED
