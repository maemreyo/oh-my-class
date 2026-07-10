from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.backpressure import BackpressureConfig
from services.gateway.models import Base, Run, TeachingBriefModel
from services.gateway.routers.teaching_briefs import router
from services.gateway.routers.teaching_pack_deps import _default_backpressure_config
from services.gateway.teaching_pack_db import get_teaching_pack_session

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
        user_id="teacher-brief-route",
        username="teacher-brief-route",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    app.dependency_overrides[_default_backpressure_config] = lambda: BackpressureConfig(
        max_active_runs_per_teacher=999_999,
        max_total_active_runs=999_999,
    )
    with TestClient(app) as test_client:
        yield test_client


def test_brief_autosaves_previews_and_launches_with_planning_review(client: TestClient) -> None:
    created = client.post("/teaching-packs/briefs", json=_brief_payload())

    assert created.status_code == 201
    brief_id = created.json()["brief_id"]
    assert created.json()["planning_review_required"] is True
    assert created.json()["materiality_reasons"] == ["rigorous_research"]

    updated = client.put(
        f"/teaching-packs/briefs/{brief_id}",
        json={**_brief_payload(), "must_include": "Fraction bars"},
    )
    preview = client.get(f"/teaching-packs/briefs/{brief_id}/contract-preview")
    launched = client.post(f"/teaching-packs/briefs/{brief_id}/launch")

    assert updated.status_code == 200
    assert updated.json()["must_include"] == "Fraction bars"
    assert preview.status_code == 200
    assert preview.json()["setup_gate"] == "contract_confirmation"
    assert preview.json()["resolved_contract"]["artifact_types"] == [
        "lesson", "worksheet", "quiz", "recap", "slide_deck",
    ]
    assert launched.status_code == 202
    assert launched.json()["status"] == "awaiting_approval"
    anyio.run(_delete_created, brief_id, launched.json()["run_id"])


def _brief_payload() -> dict[str, object]:
    return {
        "raw_request": "Teach equivalent fractions using visual models.",
        "topic": "Equivalent fractions",
        "grade": 5,
        "subject": "math",
        "research_policy": "rigorous",
    }


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.teaching_briefs" not in existing_tables:
            pytest.skip("teaching_briefs table is not present — run alembic upgrade head")
    await engine.dispose()


async def _delete_created(brief_id: str, run_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(TeachingBriefModel).where(TeachingBriefModel.brief_id == brief_id))
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
