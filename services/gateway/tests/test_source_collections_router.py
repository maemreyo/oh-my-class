"""#432: scoped Source Collection CRUD and authority-gated scope creation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base
from services.gateway.routers.source_collections import router
from services.gateway.teaching_pack_db import get_teaching_pack_session

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
TEACHER = User(user_id="teacher-sources", username="teacher-sources", role=Role.TEACHER)
OTHER_TEACHER = User(user_id="teacher-sources-other", username="teacher-sources-other", role=Role.TEACHER)


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

    app.dependency_overrides[require_teacher] = lambda: TEACHER
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


def _entry(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "District science handbook",
        "authority": "required",
        "subject_key": "boiling_point_water_celsius",
        "claim_value": "100",
    }
    payload.update(overrides)
    return payload


def test_teacher_can_create_read_and_add_entries_to_own_collection(client: TestClient) -> None:
    created = client.post(
        "/teaching-packs/source-collections",
        json={"scope": "private_teacher", "entries": [_entry()]},
    )
    assert created.status_code == 201
    collection_id = created.json()["collection_id"]
    assert len(created.json()["entries"]) == 1

    fetched = client.get(f"/teaching-packs/source-collections/{collection_id}")
    assert fetched.status_code == 200
    assert fetched.json()["owner_id"] == TEACHER.user_id

    appended = client.post(
        f"/teaching-packs/source-collections/{collection_id}/entries",
        json=_entry(title="Second textbook", authority="preferred"),
    )
    assert appended.status_code == 201
    assert len(appended.json()["entries"]) == 2


def test_teacher_cannot_create_an_organization_scoped_collection(client: TestClient) -> None:
    response = client.post(
        "/teaching-packs/source-collections",
        json={"scope": "organization", "entries": [_entry()]},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "scope_requires_higher_authority"


def test_other_teacher_cannot_read_a_private_collection(client: TestClient) -> None:
    created = client.post(
        "/teaching-packs/source-collections",
        json={"scope": "private_teacher", "entries": [_entry()]},
    )
    collection_id = created.json()["collection_id"]

    client.app.dependency_overrides[require_teacher] = lambda: OTHER_TEACHER
    forbidden = client.get(f"/teaching-packs/source-collections/{collection_id}")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "not_source_collection_owner"

    client.app.dependency_overrides[require_teacher] = lambda: TEACHER


async def _ensure_schema() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await engine.dispose()
