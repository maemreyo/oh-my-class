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
from services.gateway.teaching_pack_models import (
    ContractRevision,
    GateInterrupt,
    GateResponse,
    RunContract,
    RunJob,
)
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
        max_active_runs_per_teacher=999_999,
        max_total_active_runs=999_999,
    )
    with TestClient(app) as test_client:
        yield test_client


class TestRunContractRoutes:
    def test_missing_required_fields_open_clarification_gate(self, client: TestClient) -> None:
        response = client.post("/teaching-packs/run", json={"raw_request": " ", "class_info": {}})

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "awaiting_approval"
        assert data["job_id"] is None

        gate = anyio.run(_get_gate, RunId(data["run_id"]))
        assert gate == ("clarification_required", "active")
        anyio.run(_delete_run, RunId(data["run_id"]))

    def test_risky_defaults_open_contract_confirmation_without_start_job(
        self,
        client: TestClient,
    ) -> None:
        response = client.post(
            "/teaching-packs/run",
            json={"raw_request": "Teach fractions", "class_info": {"grade": 5, "subject": "math"}},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "awaiting_approval"
        assert data["job_id"] is None

        gate = anyio.run(_get_gate, RunId(data["run_id"]))
        assert gate == ("contract_confirmation", "active")
        anyio.run(_delete_run, RunId(data["run_id"]))

    def test_runnable_request_persists_contract_and_initial_revision(
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
        run_id = RunId(response.json()["run_id"])
        contract = anyio.run(_get_contract_revision_count, run_id)
        assert contract == (1, 1)
        anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _get_gate(run_id: RunId) -> tuple[str, str]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(GateInterrupt.gate_name, GateInterrupt.status).where(
            GateInterrupt.run_id == run_id,
        )
        result = await session.execute(statement)
        gate_name, gate_status = result.one()
    await engine.dispose()
    return gate_name, gate_status.value


async def _get_contract_revision_count(run_id: RunId) -> tuple[int, int]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        contract_result = await session.execute(
            select(RunContract.current_revision).where(RunContract.run_id == run_id),
        )
        revision_result = await session.execute(
            select(ContractRevision.revision).where(ContractRevision.run_id == run_id),
        )
        count = len(revision_result.scalars().all())
        current_revision = contract_result.scalar_one()
    await engine.dispose()
    return current_revision, count


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(ContractRevision).where(ContractRevision.run_id == run_id))
        await session.execute(delete(RunContract).where(RunContract.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
