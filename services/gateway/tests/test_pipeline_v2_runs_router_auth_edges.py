from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.pipeline_v2_control_store import GateInterruptCreate, PipelineV2ControlStore
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_models import GateInterrupt, GateResponse, RunJob
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.pipeline_v2_runs import router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def other_teacher_client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/pipeline-v2")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id="teacher-other",
        username="teacher-other",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_pipeline_v2_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestPipelineV2RunAuthEdges:
    def test_non_owner_cannot_resume_run(self, other_teacher_client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.post(
            f"/pipeline-v2/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(_delete_run, run_id)

    def test_non_owner_cannot_stream_run_status(self, other_teacher_client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.get(f"/pipeline-v2/run/{run_id}/status")

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(_delete_run, run_id)

    def test_non_owner_cannot_cancel_run(self, other_teacher_client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_owned_run_with_gate, run_id, gate_id)

        response = other_teacher_client.post(f"/pipeline-v2/run/{run_id}/cancel")

        assert response.status_code == 404
        assert response.json()["detail"] == "run_not_found"
        anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Pipeline V2 route tables are not present")
    await engine.dispose()


async def _create_owned_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-owner"),
            raw_request="Teach ownership",
            class_info={"grade": 5},
        ))
        await PipelineV2ControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"topic": "Fractions"},
        ))
        await session.commit()
    await engine.dispose()


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(GateResponse).where(GateResponse.run_id == run_id))
        await session.execute(delete(GateInterrupt).where(GateInterrupt.run_id == run_id))
        await session.execute(delete(RunJob).where(RunJob.run_id == run_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
