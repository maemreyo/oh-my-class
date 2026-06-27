from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.auth.dependencies import require_admin
from services.gateway.auth.models import Role, User
from services.gateway.models import Run
from services.gateway.pipeline_v2_db import get_pipeline_v2_session
from services.gateway.pipeline_v2_store import PipelineV2RunCreate, PipelineV2RunStore
from services.gateway.pipeline_v2_types import RunId, TeacherId
from services.gateway.routers.notifications import router

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
    app.dependency_overrides[get_pipeline_v2_session] = override_session
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


async def _create_run(run_id: RunId, teacher_id: TeacherId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await PipelineV2RunStore(session).create_run(PipelineV2RunCreate(
            run_id=run_id,
            teacher_id=teacher_id,
            raw_request="Admin list test",
            class_info={"grade": 5},
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
