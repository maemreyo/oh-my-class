from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.routers.teaching_pack_runs import router
from services.gateway.teaching_pack_control_store import (
    GateInterruptCreate,
    TeachingPackControlStore,
)
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateResponse, RunJob
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


def test_create_idempotency_key_is_scoped_to_teacher() -> None:
    anyio.run(_skip_if_schema_missing)
    idempotency_key = f"idem-{uuid4()}"
    payload = {"raw_request": "Teach fractions", "class_info": {"grade": 5}}

    with _client_for("teacher-a") as teacher_a, _client_for("teacher-b") as teacher_b:
        first = teacher_a.post(
            "/teaching-packs/run",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )
        second = teacher_b.post(
            "/teaching-packs/run",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["run_id"] != first.json()["run_id"]
    anyio.run(_delete_run, RunId(first.json()["run_id"]))
    anyio.run(_delete_run, RunId(second.json()["run_id"]))


def test_resume_idempotency_key_does_not_bypass_run_owner_check() -> None:
    anyio.run(_skip_if_schema_missing)
    run_id = RunId(f"test-{uuid4()}")
    gate_id = f"gate-{uuid4()}"
    idempotency_key = f"idem-{uuid4()}"
    anyio.run(_create_owned_run_with_gate, run_id, gate_id, TeacherId("teacher-a"))
    payload = {
        "gate_id": gate_id,
        "gate_name": "blueprint_approval",
        "action": "approve",
        "response": {"feedback": "Looks good"},
    }

    with _client_for("teacher-a") as teacher_a, _client_for("teacher-b") as teacher_b:
        first = teacher_a.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )
        second = teacher_b.post(
            f"/teaching-packs/run/{run_id}/resume",
            headers={"Idempotency-Key": idempotency_key},
            json=payload,
        )

    assert first.status_code == 202
    assert second.status_code == 404
    assert second.json()["detail"] == "run_not_found"
    anyio.run(_delete_run, run_id)


def _client_for(teacher_id: str) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id=teacher_id,
        username=teacher_id,
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    from services.gateway.backpressure import BackpressureConfig
    from services.gateway.routers.teaching_pack_runs import _default_backpressure_config
    app.dependency_overrides[_default_backpressure_config] = lambda: BackpressureConfig(
        max_active_runs_per_teacher=999_999,
        max_total_active_runs=999_999,
    )
    return TestClient(app)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.run_jobs" not in existing_tables:
            pytest.skip("Teaching Pack route tables are not present")
    await engine.dispose()


async def _create_owned_run_with_gate(
    run_id: RunId,
    gate_id: str,
    teacher_id: TeacherId,
) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Teach ownership",
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
