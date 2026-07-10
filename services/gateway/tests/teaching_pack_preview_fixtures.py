from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from packages.agents.config.features import reset_features
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base
from services.gateway.routers.teaching_pack_previews import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.tests.teaching_pack_preview_db import DATABASE_URL

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(autouse=True)
def _slide_deck_flags_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """SDE-10: this module's existing tests exercise manual edit and AI
    rewrite as already-enabled features -- default both flags on here, and
    let the small number of gating-specific tests disable one explicitly.
    """
    monkeypatch.setenv("FEATURE_SLIDE_DECK_EDITOR_V1", "true")
    monkeypatch.setenv("FEATURE_SLIDE_DECK_AI_REWRITE_V1", "true")
    reset_features()
    yield
    reset_features()


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
        user_id="teacher-preview",
        username="teacher-preview",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_teacher_client() -> Iterator[TestClient]:
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
        user_id="teacher-other",
        username="teacher-other",
        role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda _: set(Base.metadata.tables),
        )
        if "public.artifact_snapshots" not in existing_tables:
            pytest.skip("Teaching Pack snapshot tables are not present")
    await engine.dispose()
