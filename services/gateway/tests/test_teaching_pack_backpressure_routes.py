from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.backpressure import BackpressureConfig
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import _default_backpressure_config, router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunContract, RunJob, RunJobStatus
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-route",
        username="teacher-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    app.dependency_overrides[_default_backpressure_config] = lambda: BackpressureConfig(
        max_active_runs_per_teacher=0,
        max_queued_runs_per_teacher=5,
        max_total_active_runs=999_999,
        max_total_queued_runs=999_999,
    )
    with TestClient(app) as test_client:
        yield test_client


class TestTeachingPackBackpressureRoutes:
    def test_create_run_returns_ui_visible_queued_state_when_active_limit_is_full(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/teaching-packs/run",
            json={
                "raw_request": "Fractions",
                "class_info": {"topic": "Fractions", "grade": 5, "subject": "math"},
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["queued"] is True
        assert data["job_id"]
        assert anyio.run(_get_job_status, RunId(data["run_id"]), data["job_id"]) is RunJobStatus.QUEUED
        anyio.run(_delete_run, RunId(data["run_id"]))


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _get_job_status(run_id: RunId, job_id: str) -> RunJobStatus:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(RunJob.status).where(RunJob.run_id == run_id, RunJob.job_id == job_id),
        )
        status = result.scalar_one()
    await engine.dispose()
    return status


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(RunContract).where(RunContract.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
