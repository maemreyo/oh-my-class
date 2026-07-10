"""#433: Content Brief creation, append-only strategy review, and compliance verification."""

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
from services.gateway.routers.content_briefs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(user_id="teacher-brief-owner", username="teacher-brief-owner", role=Role.TEACHER)


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_ensure_schema)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-packs")

    async def override_session() -> AsyncIterator[AsyncSession]:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[require_teacher] = lambda: OWNER
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


def _seed_run() -> str:
    run_id = f"test-{uuid4()}"

    async def _create() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
                run_id=RunId(run_id),
                teacher_id=TeacherId(OWNER.user_id),
                raw_request="Build a recap",
                class_info={"grade": 5},
            ))
            await session.commit()
        await engine.dispose()

    anyio.run(_create)
    return run_id


def _brief_payload() -> dict[str, object]:
    return {
        "artifact_type": "recap",
        "objectives": ["explain photosynthesis"],
        "methodology": "direct_instruction",
        "methodology_source": "teacher_pin",
        "learning_moves": ["explain", "model"],
    }


def test_specialist_deviation_is_rejected_and_routes_to_strategy_review(client: TestClient) -> None:
    run_id = _seed_run()

    created = client.post(f"/teaching-packs/runs/{run_id}/content-briefs", json=_brief_payload())
    assert created.status_code == 201
    content_brief_id = created.json()["content_brief_id"]

    fetched = client.get(f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}")
    assert fetched.status_code == 200
    assert fetched.json()["objectives"] == ["explain photosynthesis"]

    compliant = client.post(
        f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}/verify-compliance",
        json={"methodology": "direct_instruction", "objectives_covered": ["explain photosynthesis"]},
    )
    assert compliant.status_code == 204

    deviated = client.post(
        f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}/verify-compliance",
        json={"methodology": "inquiry_based", "objectives_covered": ["explain photosynthesis"]},
    )
    assert deviated.status_code == 409
    assert deviated.json()["detail"]["error"] == "content_brief_compliance_violation"

    fill_failure = client.post(
        f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}/fill-failures",
        json={"reason": "insufficient_evidence", "detail": "No verified source covers this objective."},
    )
    assert fill_failure.status_code == 201

    change_request = client.post(
        f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}/strategy-change-requests",
        json={"change_kind": "methodology_change", "rationale": "Direct instruction does not fit this cohort."},
    )
    assert change_request.status_code == 201

    review = client.get(f"/teaching-packs/runs/{run_id}/content-briefs/{content_brief_id}/review")
    assert review.status_code == 200
    request_types = [entry["request_type"] for entry in review.json()]
    assert request_types == ["fill_failure", "strategy_change"]
    assert all(entry["status"] == "open" for entry in review.json())

    anyio.run(_delete_created, run_id)


def test_unknown_content_brief_returns_404(client: TestClient) -> None:
    run_id = _seed_run()

    response = client.get(f"/teaching-packs/runs/{run_id}/content-briefs/brief-does-not-exist")

    assert response.status_code == 404
    anyio.run(_delete_created, run_id)


async def _ensure_schema() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def _delete_created(run_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
