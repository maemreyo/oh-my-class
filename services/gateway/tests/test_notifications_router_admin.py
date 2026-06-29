from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import Role, User
from services.gateway.models import Run, RunStatus
from services.gateway.routers.notifications import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import GateInterrupt, GateInterruptStatus
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router, prefix="/notifications")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_admin] = lambda: User(
        user_id="admin-test",
        username="admin-test",
        role=Role.SYSTEM_ADMIN,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


class TestAdminRunListEndpoint:
    async def test_lists_runs_filtered_by_teacher(self, client: TestClient) -> None:
        run_id = RunId(f"admin-list-{uuid4()}")
        await _create_run(run_id, TeacherId("teacher-list"))

        response = client.get("/notifications/admin/runs?teacher_id=teacher-list&limit=5")

        assert response.status_code == 200
        assert any(item["run_id"] == run_id for item in response.json()["runs"])
        await _delete_run(run_id)

    async def test_lists_failed_runs_by_operational_filter(self, client: TestClient) -> None:
        failed_run_id = RunId(f"admin-list-failed-{uuid4()}")
        pending_run_id = RunId(f"admin-list-pending-{uuid4()}")
        await _create_run(failed_run_id, TeacherId("teacher-list"), status=RunStatus.FAILED)
        await _create_run(pending_run_id, TeacherId("teacher-list"))

        response = client.get("/notifications/admin/runs?operational_filter=failed&limit=20")

        assert response.status_code == 200
        run_ids = {item["run_id"] for item in response.json()["runs"]}
        assert failed_run_id in run_ids
        assert pending_run_id not in run_ids
        await _delete_run(failed_run_id)
        await _delete_run(pending_run_id)

    async def test_lists_awaiting_gate_runs_by_operational_filter(
        self,
        client: TestClient,
    ) -> None:
        gated_run_id = RunId(f"admin-list-gated-{uuid4()}")
        pending_run_id = RunId(f"admin-list-ungated-{uuid4()}")
        await _create_run(gated_run_id, TeacherId("teacher-list"))
        await _create_run(pending_run_id, TeacherId("teacher-list"))
        await _create_gate(gated_run_id)

        response = client.get("/notifications/admin/runs?operational_filter=awaiting_gate&limit=20")

        assert response.status_code == 200
        run_ids = {item["run_id"] for item in response.json()["runs"]}
        assert gated_run_id in run_ids
        assert pending_run_id not in run_ids
        await _delete_run(gated_run_id)
        await _delete_run(pending_run_id)


async def _create_run(
    run_id: RunId,
    teacher_id: TeacherId,
    status: RunStatus = RunStatus.PENDING,
) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Admin list test",
            class_info={"grade": 5},
        ))
        statement = select(Run).where(Run.run_id == run_id).with_for_update()
        run = (await session.execute(statement)).scalar_one()
        run.status = status
        await session.commit()
    await engine.dispose()


async def _create_gate(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        session.add(GateInterrupt(
            gate_id=f"gate-admin-list-{uuid4()}",
            run_id=run_id,
            gate_name="content_approval",
            status=GateInterruptStatus.ACTIVE,
            payload={"gate": "content_approval"},
        ))
        await session.commit()
    await engine.dispose()


async def _delete_run(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
