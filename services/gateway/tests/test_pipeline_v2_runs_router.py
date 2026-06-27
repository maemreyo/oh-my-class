from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.backpressure import BackpressureConfig
from services.gateway.models import Base, Run
from services.gateway.pipeline_v2_control_store import GateInterruptCreate, PipelineV2ControlStore
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_models import (
    GateInterrupt,
    GateResponse,
    PipelineV2EventVisibility,
    RunJob,
    RunJobKind,
)
from services.gateway.pipeline_v2_store import (
    PipelineV2EventCreate,
    PipelineV2RunCreate,
    PipelineV2RunStore,
)
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.pipeline_v2_runs import _default_backpressure_config, router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def client() -> Iterator[TestClient]:
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
        user_id="teacher-route",
        username="teacher-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_pipeline_v2_session] = override_session
    app.dependency_overrides[_default_backpressure_config] = lambda: BackpressureConfig(
        max_active_runs_per_teacher=999_999,
        max_total_active_runs=999_999,
    )
    with TestClient(app) as test_client:
        yield test_client


class TestPipelineV2RunsRouter:
    def test_create_run_persists_run_and_start_job(self, client: TestClient) -> None:
        payload = {
            "raw_request": "Fractions",
            "class_info": {"topic": "Fractions", "grade": 5, "subject": "math"},
        }
        response = client.post("/pipeline-v2/run", json=payload)

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "pending"
        assert data["run_id"]
        assert data["job_id"]

        job_kind = anyio.run(_get_job_kind, RunId(data["run_id"]), data["job_id"])
        assert job_kind is RunJobKind.START
        anyio.run(_delete_run, RunId(data["run_id"]))

    def test_resume_persists_gate_response_and_resume_job(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)

        response = client.post(
            f"/pipeline-v2/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
                "response": {"feedback": "Looks good"},
            },
        )

        assert response.status_code == 202
        data = response.json()
        assert data["run_id"] == run_id

        persisted = anyio.run(_get_resume_result, run_id, data["job_id"])
        assert persisted == (RunJobKind.RESUME, "approve")
        anyio.run(_delete_run, run_id)

    def test_resume_rejects_action_not_allowed_for_gate(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)

        response = client.post(
            f"/pipeline-v2/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "clarification_required",
                "action": "approve",
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "action_not_allowed"
        anyio.run(_delete_run, run_id)

    def test_status_stream_replays_teacher_events_after_last_event_id(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_run_with_events, run_id)

        response = client.get(
            f"/pipeline-v2/run/{run_id}/status?replay_only=true",
            headers={"Last-Event-ID": "1"},
        )

        assert response.status_code == 200
        assert "event: pipeline_v2.visible" in response.text
        assert "id: 3" in response.text
        assert "event: pipeline_v2.internal" not in response.text
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


async def _get_job_kind(run_id: RunId, job_id: str) -> RunJobKind:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(RunJob.kind).where(RunJob.run_id == run_id, RunJob.job_id == job_id)
        result = await session.execute(statement)
        return result.scalar_one()


async def _get_resume_result(run_id: RunId, job_id: str) -> tuple[RunJobKind, str]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        job_statement = select(RunJob.kind).where(RunJob.run_id == run_id, RunJob.job_id == job_id)
        job_result = await session.execute(job_statement)
        response_statement = select(GateResponse.response_json).where(GateResponse.run_id == run_id)
        response_result = await session.execute(response_statement)
        return job_result.scalar_one(), response_result.scalar_one()["action"]


async def _create_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        teacher_id = TeacherId("teacher-route")
        await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach approval",
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


async def _create_run_with_events(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        teacher_id = TeacherId("teacher-route")
        store = PipelineV2RunStore(session)
        await store.create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach streaming",
            class_info={"grade": 5},
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.hidden",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"step": 1},
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.internal",
            visibility=PipelineV2EventVisibility.INTERNAL,
            payload={"step": 2},
        ))
        await store.write_event(PipelineV2EventCreate(
            run_id=run_id,
            event_name="pipeline_v2.visible",
            visibility=PipelineV2EventVisibility.TEACHER,
            payload={"step": 3},
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
