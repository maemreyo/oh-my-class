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
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    RunContractCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunContract, RunJob, RunJobKind
from services.gateway.teaching_pack_models import RunEvent
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
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestTeachingPackContractResume:
    def test_contract_confirmation_resume_enqueues_start_job_with_contract(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_contract_gate, run_id, gate_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "contract_confirmation",
                "action": "approve",
                "response": {"feedback": "Looks good"},
            },
        )

        assert response.status_code == 202
        data = response.json()
        kind, job_payload = anyio.run(_get_job_result, run_id, data["job_id"])
        assert kind is RunJobKind.START
        assert job_payload["contract"]["topic"] == "Fractions"
        assert job_payload["contract"]["run_id"] == run_id
        anyio.run(_delete_run, run_id)

    def test_contract_confirmation_opens_search_plan_gate_when_confirmation_required(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_vi_curriculum_run_with_contract_gate, run_id, gate_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "contract_confirmation",
                "action": "approve",
                "response": {},
            },
        )

        assert response.status_code == 202
        data = response.json()
        gate, event_names, job_count = anyio.run(_get_search_gate_result, run_id)
        assert data["job_id"] is None
        assert gate == ("search_plan_confirmation", "active")
        assert "teaching_pack.search_plan_confirmation.opened" in event_names
        assert job_count == 0
        anyio.run(_delete_run, run_id)

    def test_search_plan_confirmation_resume_enqueues_start_job_with_contract(
        self,
        client: TestClient,
    ) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_vi_curriculum_run_with_contract_gate, run_id, gate_id)
        contract_response = client.post(
            f"/teaching-packs/runs/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "contract_confirmation",
                "action": "approve",
                "response": {},
            },
        )
        assert contract_response.status_code == 202
        search_gate_id = anyio.run(_active_gate_id, run_id, "search_plan_confirmation")

        response = client.post(
            f"/teaching-packs/runs/{run_id}/resume",
            json={
                "gate_id": search_gate_id,
                "gate_name": "search_plan_confirmation",
                "action": "approve",
                "response": {"approved_query_ids": []},
            },
        )

        assert response.status_code == 202
        data = response.json()
        kind, job_payload = anyio.run(_get_job_result, run_id, data["job_id"])
        assert kind is RunJobKind.START
        assert job_payload["contract"]["run_id"] == run_id
        assert job_payload["resume_payload"]["action"] == "approve"
        anyio.run(_delete_run, run_id)

    def test_contract_edit_rejects_immutable_field_overwrites(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        gate_id = f"gate-{uuid4()}"
        anyio.run(_create_run_with_contract_gate, run_id, gate_id)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/resume",
            json={
                "gate_id": gate_id,
                "gate_name": "contract_confirmation",
                "action": "edit",
                "response": {
                    "edits": {
                        "topic": "Equivalent fractions",
                        "teacher_id": "attacker-teacher",
                        "run_id": "attacker-run",
                        "config_hash": "f" * 64,
                    },
                },
            },
        )

        assert response.status_code == 202
        contract_json = anyio.run(_get_contract_json, run_id)
        assert contract_json["topic"] == "Equivalent fractions"
        assert contract_json["teacher_id"] == "teacher-route"
        assert contract_json["run_id"] == run_id
        assert contract_json["config_hash"] == "0" * 64
        anyio.run(_delete_run, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda sync_connection: set(Base.metadata.tables))
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_run_with_contract_gate(
    run_id: RunId,
    gate_id: str,
    *,
    curriculum: str | None = "Common Core",
    locale: str = "en-US",
) -> None:
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
        contract: JsonObject = {
            "contract_id": f"contract-{run_id}",
            "run_id": run_id,
            "teacher_id": teacher_id,
            "topic": "Fractions",
            "grade_band": "Grade 5",
            "subject": "math",
            "locale": locale,
            "instruction_language": "en",
            "curriculum": curriculum,
            "citation_locale": locale,
            "artifact_types": ["lesson"],
            "export_formats": ["html"],
            "research_policy": "standard",
            "config_version": "test",
            "config_hash": "0" * 64,
            "revision_meta": {
                "revision": 1,
                "actor": "system",
                "source": "request",
                "reason": "test",
                "effective_stage": "setup_contract",
            },
        }
        control_store = TeachingPackControlStore(session)
        await control_store.create_contract(RunContractCreate(
            contract_id=str(contract["contract_id"]),
            run_id=run_id,
            teacher_id=teacher_id,
            contract_json=contract,
        ))
        await control_store.open_gate(GateInterruptCreate(
            gate_id=gate_id,
            run_id=run_id,
            gate_name="contract_confirmation",
            payload={"contract": contract},
        ))
        await session.commit()
    await engine.dispose()


async def _create_vi_curriculum_run_with_contract_gate(run_id: RunId, gate_id: str) -> None:
    await _create_run_with_contract_gate(run_id, gate_id, curriculum=None, locale="vi-VN")


async def _get_job_result(run_id: RunId, job_id: str) -> tuple[RunJobKind, JsonObject]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(RunJob.kind, RunJob.payload).where(
            RunJob.run_id == run_id,
            RunJob.job_id == job_id,
        ))
        row = result.one()
    await engine.dispose()
    return row[0], row[1]


async def _get_search_gate_result(run_id: RunId) -> tuple[tuple[str, str], list[str], int]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        gate_result = await session.execute(
            select(GateInterrupt.gate_name, GateInterrupt.status).where(
                GateInterrupt.run_id == run_id,
                GateInterrupt.gate_name == "search_plan_confirmation",
            ),
        )
        event_result = await session.execute(
            select(RunEvent.event_name).where(RunEvent.run_id == run_id),
        )
        job_result = await session.execute(select(RunJob).where(RunJob.run_id == run_id))
        gate = gate_result.one()
        events = list(event_result.scalars().all())
        job_count = len(job_result.scalars().all())
    await engine.dispose()
    return (gate[0], gate[1].value), events, job_count


async def _get_contract_json(run_id: RunId) -> JsonObject:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(select(RunContract.contract_json).where(RunContract.run_id == run_id))
        contract_json = result.scalar_one()
    await engine.dispose()
    return contract_json


async def _active_gate_id(run_id: RunId, gate_name: str) -> str:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(GateInterrupt.gate_id).where(
                GateInterrupt.run_id == run_id,
                GateInterrupt.gate_name == gate_name,
                GateInterrupt.status == "active",
            ),
        )
        gate_id = result.scalar_one()
    await engine.dispose()
    return gate_id


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
