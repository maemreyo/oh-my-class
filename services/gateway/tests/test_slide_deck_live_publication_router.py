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
from services.gateway.models import Base
from services.gateway.routers.slide_deck_live_publication import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId
from services.gateway.teaching_session.models import TeachingSession
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL
from services.gateway.tests.teaching_pack_preview_helpers import delete_run

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


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
        user_id="teacher-live-pub",
        username="teacher-live-pub",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.teaching_sessions" not in existing_tables:
            pytest.skip("teaching_sessions table is not present (run alembic upgrade head)")
    await engine.dispose()


async def _seed_slide_deck_snapshot(run_id: RunId, approve: bool) -> str:
    # ponytail: anyio.run only forwards positional args, so `approve` is
    # positional here rather than keyword-only.
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=run_id,
            teacher_id=TeacherId("teacher-live-pub"),
            raw_request="Test slide deck live publication",
            class_info={"grade": 5},
        ))
        snapshot_store = TeachingPackSnapshotStore(session)
        snapshot = await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
            snapshot_id=f"snap-{uuid4()}",
            run_id=run_id,
            artifact_id="deck-1",
            artifact_type="slide_deck",
            content_json={"deck_id": "deck-1", "title": f"Deck {run_id}"},
            rendered_html=f"<!DOCTYPE html><html><body>oh-my-class deck {run_id}</body></html>",
            renderer_version="1.0",
        ))
        if approve:
            await snapshot_store.approve_snapshots(run_id, [snapshot.snapshot_id])
        await session.commit()
        snapshot_id = snapshot.snapshot_id
    await engine.dispose()
    return snapshot_id


async def _delete_published_sessions(run_id: RunId) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(TeachingSession).where(TeachingSession.deck_id == "deck-1"))
        await session.commit()
    await engine.dispose()
    await delete_run(run_id)


class TestSlideDeckLivePublicationRouter:
    def test_publish_pins_the_live_session_to_the_approved_snapshot(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        snapshot_id = anyio.run(_seed_slide_deck_snapshot, run_id, True)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/deck-1/publish-live-session", json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["snapshot_id"] == snapshot_id
        assert data["room_code"] is not None
        assert data["session_id"]
        anyio.run(_delete_published_sessions, run_id)

    def test_publish_rejects_an_unapproved_slide_deck(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        anyio.run(_seed_slide_deck_snapshot, run_id, False)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/deck-1/publish-live-session", json={},
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "slide_deck_not_approved"
        anyio.run(delete_run, run_id)

    def test_publish_rejects_a_non_slide_deck_artifact(self, client: TestClient) -> None:
        run_id = RunId(f"test-{uuid4()}")
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

        async def seed() -> None:
            session_factory = async_sessionmaker(engine, expire_on_commit=False)
            async with session_factory() as session:
                await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
                    run_id=run_id,
                    teacher_id=TeacherId("teacher-live-pub"),
                    raw_request="Test non slide deck publish rejection",
                    class_info={"grade": 5},
                ))
                snapshot_store = TeachingPackSnapshotStore(session)
                snapshot = await snapshot_store.create_snapshot(ArtifactSnapshotCreate(
                    snapshot_id=f"snap-{uuid4()}",
                    run_id=run_id,
                    artifact_id="lesson-1",
                    artifact_type="lesson",
                    content_json={"title": "Not a deck"},
                    rendered_html=f"<!DOCTYPE html><html><body>oh-my-class lesson {run_id}</body></html>",
                    renderer_version="1.0",
                ))
                await snapshot_store.approve_snapshots(run_id, [snapshot.snapshot_id])
                await session.commit()
            await engine.dispose()

        anyio.run(seed)

        response = client.post(
            f"/teaching-packs/runs/{run_id}/artifacts/lesson-1/publish-live-session", json={},
        )

        assert response.status_code == 422
        assert response.json()["detail"]["error"] == "not_a_slide_deck"
        anyio.run(delete_run, run_id)
