from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

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
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    RunContractCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import (
    ContractRevision,
    GateInterrupt,
    GateResponse,
    RunContract,
    RunJob,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

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


class TestTeachingPackRunRouteEdges:
    def test_create_same_idempotency_key_with_different_body_returns_409(
        self,
        client: TestClient,
    ) -> None:
        idempotency_key = f"idem-{uuid4()}"
        first = client.post(
            "/teaching-packs/run",
            headers={"Idempotency-Key": idempotency_key},
            json={"raw_request": "Teach decimals", "class_info": {"grade": 4}},
        )
        second = client.post(
            "/teaching-packs/run",
            headers={"Idempotency-Key": idempotency_key},
            json={"raw_request": "Teach fractions", "class_info": {"grade": 4}},
        )

        assert second.status_code == 409
        assert second.json()["detail"] == "idempotency_conflict"
        anyio.run(_delete_run, RunId(first.json()["run_id"]))

    def test_resume_same_idempotency_key_returns_same_response(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        idempotency_key = f"idem-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)
        payload = {
            "gate_id": gate_id,
            "gate_name": "blueprint_approval",
            "action": "approve",
            "response": {"feedback": "Looks good"},
        }

        first = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )
        second = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )

        assert second.status_code == 202
        assert second.json() == first.json()
        anyio.run(_delete_run, run_id)

    def test_resume_same_idempotency_key_with_different_body_returns_409(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        idempotency_key = f"idem-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)

        first = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
                "response": {"feedback": "Looks good"},
            },
        )
        second = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json={
                "gate_id": gate_id,
                "gate_name": "blueprint_approval",
                "action": "approve",
                "response": {"feedback": "Changed"},
            },
        )

        assert first.status_code == 202
        assert second.status_code == 409
        assert second.json()["detail"] == "idempotency_conflict"
        anyio.run(_delete_run, run_id)

    def test_resume_stale_gate_without_idempotency_key_returns_409(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_gate, run_id, gate_id)
        payload = {
            "gate_id": gate_id,
            "gate_name": "blueprint_approval",
            "action": "approve",
            "response": {"feedback": "Looks good"},
        }

        first = client.post(f"/teaching-packs/run/{run_id}/resume", json=payload)
        second = client.post(f"/teaching-packs/run/{run_id}/resume", json=payload)

        assert first.status_code == 202
        assert second.status_code == 409
        assert second.json()["detail"] == "stale_gate"
        anyio.run(_delete_run, run_id)

    def test_resume_edit_creates_next_contract_revision(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_contract_gate, run_id, gate_id)

        response = client.post(
            f"/teaching-packs/run/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "contract_confirmation",
                "action": "edit",
                "response": {"edits": {"duration_minutes": 60}},
            },
        )
        revision_count = anyio.run(_contract_revision_count, run_id)

        assert response.status_code == 202
        assert revision_count == 2
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


async def _create_run_with_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        teacher_id = TeacherId("teacher-route")
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach approval",
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


async def _create_run_with_contract_gate(run_id: RunId, gate_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        teacher_id = TeacherId("teacher-route")
        contract_json = {
            "topic": "Fractions",
            "grade_level": "Grade 5",
            "duration_minutes": 45,
        }
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach approval",
            class_info={"grade": 5},
        ))
        await TeachingPackControlStore(session).create_contract(RunContractCreate(
            contract_id=f"contract-{run_id}",
            run_id=run_id,
            teacher_id=teacher_id,
            contract_json=contract_json,
        ))
        await TeachingPackControlStore(session).open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="contract_confirmation",
            payload={"contract": contract_json},
        ))
        await session.commit()
    await engine.dispose()


async def _contract_revision_count(run_id: RunId) -> int:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(ContractRevision).where(ContractRevision.run_id == run_id),
        )
        count = len(result.scalars().all())
    await engine.dispose()
    return count


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
