from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import get_current_user_for_status_stream, require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run, RunStatus
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_job_store import RunJobCreate, TeachingPackJobStore
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    GateResponse,
    RunEvent,
    RunJob,
    RunJobKind,
)
from services.gateway.teaching_pack_control_store import GateInterruptCreate, TeachingPackControlStore
from services.gateway.teaching_pack_gate_registry import TeachingPackGateName, allowed_actions_for_gate
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, RunId, TeacherId

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
    app.dependency_overrides[get_current_user_for_status_stream] = lambda: User(
        user_id="teacher-route",
        username="teacher-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestTeachingPackLifecycle:
    def test_cancel_persists_actor_reason_and_cancelled_job_count(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_run_with_jobs, run_id)

        response = client.post(f"/teaching-packs/run/{run_id}/cancel")
        stream = client.get(f"/teaching-packs/run/{run_id}/status?replay_only=true")

        assert response.status_code == 200
        assert response.json() == {
            "run_id": run_id,
            "status": "cancelled",
            "cancelled_jobs": 2,
        }
        assert anyio.run(_get_cancel_event_payload, run_id) == {
            "actor_id": "teacher-route",
            "reason": "teacher_cancelled",
            "cancelled_jobs": 2,
            "cancelled_gates": 0,
        }
        assert "event: teaching_pack.run.cancelled" in stream.text
        assert '"cancelled_jobs":2' in stream.text
        anyio.run(_assert_run_status, run_id, RunStatus.CANCELLED)
        anyio.run(_delete_run, run_id)

    def test_cancel_closes_active_gate_and_blocks_later_resume(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)

        cancel = client.post(f"/teaching-packs/run/{run_id}/cancel")
        resume = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
                "response": {"feedback": "Too late"},
            },
        )

        assert cancel.status_code == 200
        assert resume.status_code == 409
        assert resume.json()["detail"] == "stale_gate"
        assert anyio.run(_get_cancel_event_payload, run_id)["cancelled_gates"] == 1
        assert anyio.run(_get_gate_status, gate_id) is GateInterruptStatus.CANCELLED
        anyio.run(_delete_run, run_id)

    def test_run_status_exposes_pending_content_approval_gate(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_awaiting_run_with_content_gate, run_id, gate_id)

        response = client.get(f"/teaching-packs/runs/{run_id}")

        assert response.status_code == 200
        pending_gate = response.json()["pending_gate"]
        assert pending_gate == {
            "gate_id": gate_id,
            "gate_name": "content_approval",
            "allowed_actions": [
                action.value
                for action in allowed_actions_for_gate(TeachingPackGateName.CONTENT_APPROVAL)
            ],
            "snapshot_ids": ["snap-a", "snap-b"],
        }
        anyio.run(_delete_run, run_id)

    def test_run_status_has_null_pending_gate_when_no_gate_is_open(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_create_run_without_gate, run_id)

        response = client.get(f"/teaching-packs/runs/{run_id}")

        assert response.status_code == 200
        assert response.json()["pending_gate"] is None
        anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_run_with_jobs(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach cancellation",
            class_info={"grade": 5},
        ))
        store = TeachingPackJobStore(session)
        await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.START,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "cancel-test"},
        ))
        await store.enqueue(RunJobCreate(
            job_id=f"job-{uuid4()}",
            run_id=run_id,
            kind=RunJobKind.RESUME,
            idempotency_key=f"idem-{uuid4()}",
            payload={"source": "cancel-test"},
        ))
        await session.commit()
    await engine.dispose()


async def _create_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach cancellation gate",
            class_info={"grade": 5},
        ))
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="blueprint_approval",
            payload={"topic": "Fractions"},
        ))
        await session.commit()
    await engine.dispose()


async def _create_awaiting_run_with_content_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach gate discovery",
            class_info={"grade": 5},
        ))
        run = await session.get(Run, run_id)
        assert run is not None
        run.status = RunStatus.AWAITING_APPROVAL
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="content_approval",
            payload={"snapshot_ids": ["snap-a", "snap-b"]},
        ))
        await session.commit()
    await engine.dispose()


async def _create_run_without_gate(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-route"),
            raw_request="Teach no gate",
            class_info={"grade": 5},
        ))
        await session.commit()
    await engine.dispose()


async def _get_cancel_event_payload(run_id: RunId) -> JsonObject:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(RunEvent.payload).where(
                RunEvent.run_id == run_id,
                RunEvent.event_name == "teaching_pack.run.cancelled",
            ),
        )
        payload = result.scalar_one()
    await engine.dispose()
    assert isinstance(payload, dict)
    return payload


async def _get_gate_status(gate_id: str) -> GateInterruptStatus:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(GateInterrupt.status).where(GateInterrupt.gate_id == gate_id),
        )
        status = result.scalar_one()
    await engine.dispose()
    return status


async def _assert_run_status(run_id: RunId, status: RunStatus) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        run = await session.get(Run, run_id)
        assert run is not None
        assert run.status is status
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
