"""#124: ops-admin inspection and replay endpoints for dead-lettered jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.routers.ops import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import RunJob, RunJobKind
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
ADMIN = User(user_id="admin-dlq", username="admin-dlq", role=Role.SYSTEM_ADMIN)


async def _ensure_schema() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_ensure_schema)
    app = FastAPI()
    app.include_router(router)

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_admin] = lambda: ADMIN
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _create_dead_lettered_job(run_id: RunId) -> str:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-dlq-router"),
            raw_request="Teach dead-letter router",
            class_info={"grade": 5},
        ))
        await session.flush()
        store = TeachingPackJobStore(session)
        await store.enqueue(RunJobCreate(
            job_id=f"job-dlq-router-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-dlq-router-{uuid4()}",
            payload={"initial_state": {"run_id": run_id}},
        ))
        claimed = await store.claim_next(
            lease_owner="worker-dlq-router", lease_seconds=30, now=datetime(2026, 1, 1, tzinfo=UTC),
        )
        assert claimed is not None
        await store.mark_dead_letter(
            claimed.job_id, error_summary="permanent failure for router test", classification="permanent",
        )
        await session.commit()
        job_id = claimed.job_id
    await engine.dispose()
    return job_id


async def _cleanup(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()


class TestOpsDeadLetterRouter:
    def test_admin_can_list_dead_letter_jobs(self, client: TestClient) -> None:
        run_id = RunId(f"test-dlq-router-{uuid4()}")
        job_id = anyio.run(_create_dead_lettered_job, run_id)
        try:
            response = client.get("/ops/dead-letter-jobs")

            assert response.status_code == 200
            jobs = response.json()["jobs"]
            matching = [job for job in jobs if job["job_id"] == job_id]
            assert len(matching) == 1
            assert matching[0]["error_classification"] == "permanent"
            assert matching[0]["last_error"] == "permanent failure for router test"
            assert matching[0]["dead_lettered_at"] is not None
        finally:
            anyio.run(_cleanup, run_id)

    def test_admin_can_replay_a_dead_letter_job(self, client: TestClient) -> None:
        run_id = RunId(f"test-dlq-router-{uuid4()}")
        job_id = anyio.run(_create_dead_lettered_job, run_id)
        try:
            response = client.post(f"/ops/dead-letter-jobs/{job_id}/replay")

            assert response.status_code == 200
            assert response.json() == {"job_id": job_id, "replayed": True}

            follow_up = client.get("/ops/dead-letter-jobs")
            job_ids = {job["job_id"] for job in follow_up.json()["jobs"]}
            assert job_id not in job_ids
        finally:
            anyio.run(_cleanup, run_id)

    def test_replaying_an_unknown_job_id_404s(self, client: TestClient) -> None:
        response = client.post("/ops/dead-letter-jobs/does-not-exist/replay")

        assert response.status_code == 404
