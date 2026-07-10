"""#434: Media Asset version CRUD, dependency-blocked deletion, and Visual Source Suggestions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    DocumentBlock,
    DocumentSection,
)
from services.gateway.artifact_document_store import ArtifactDocumentStore, ArtifactDocumentWrite
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.models import Base, Run
from services.gateway.routers.media_asset_versions import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(user_id="teacher-media-owner", username="teacher-media-owner", role=Role.TEACHER)
STRANGER = User(user_id="teacher-media-stranger", username="teacher-media-stranger", role=Role.TEACHER)


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


async def _seed_run_with_document(artifact_id: str) -> tuple[str, str]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    run_id = f"test-{uuid4()}"
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=RunId(run_id),
            teacher_id=TeacherId(OWNER.user_id),
            raw_request="Build an infographic",
            class_info={"grade": 5},
        ))
        document = ArtifactDocument(
            document_id=f"document-{uuid4()}",
            artifact_id=artifact_id,
            artifact_type="infographic",
            version=1,
            language="en",
            audience="student",
            authority="generated",
            payload=ArtifactPayload(
                payload_kind="block_document",
                sections=[DocumentSection(
                    entity_id="section-1",
                    title="Infographic",
                    blocks=[DocumentBlock(entity_id="block-1", block_kind="paragraph", text="Plant cell diagram")],
                )],
            ),
        )
        await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=RunId(run_id), document=document))
        await session.commit()
        document_id = document.document_id
    await engine.dispose()
    return run_id, document_id


def _upload(client: TestClient, *, filename: str = "cell.png") -> dict[str, object]:
    response = client.post(
        "/teaching-packs/media-asset-versions",
        files={"file": (filename, b"\x89PNG-fake-bytes", "image/png")},
        data={"scope": "private_teacher", "alt_text": "A labeled diagram of a plant cell."},
    )
    assert response.status_code == 201
    return response.json()


def test_upload_replace_and_dependency_blocked_deletion(client: TestClient) -> None:
    run_id, document_id = anyio.run(_seed_run_with_document, "infographic-router-1")

    created = _upload(client)
    asset_id = created["asset_id"]
    assert created["version"] == 1
    assert len(created["checksum_sha256"]) == 64

    fetched_file = client.get(f"/teaching-packs/media-asset-versions/{asset_id}/file")
    assert fetched_file.status_code == 200
    assert fetched_file.content == b"\x89PNG-fake-bytes"

    linked = client.post(
        f"/teaching-packs/media-asset-versions/{asset_id}/dependencies",
        json={"document_id": document_id},
    )
    assert linked.status_code == 201

    blocked_delete = client.delete(f"/teaching-packs/media-asset-versions/{asset_id}")
    assert blocked_delete.status_code == 409
    assert blocked_delete.json()["detail"]["dependent_document_ids"] == [document_id]

    replaced = client.post(
        f"/teaching-packs/media-asset-versions/{asset_id}/replace",
        files={"file": ("cell-v2.png", b"different-bytes", "image/png")},
        data={"alt_text": "An updated labeled diagram."},
    )
    assert replaced.status_code == 201
    assert replaced.json()["version"]["version"] == 2
    assert replaced.json()["impacted_document_ids"] == [document_id]

    versions = client.get(f"/teaching-packs/media-asset-versions/{asset_id}/versions")
    assert [v["version"] for v in versions.json()] == [2, 1]

    anyio.run(_delete_created, run_id)


def test_stranger_cannot_read_another_teachers_asset(client: TestClient) -> None:
    anyio.run(_seed_run_with_document, "infographic-router-2")
    created = _upload(client)
    asset_id = created["asset_id"]

    client.app.dependency_overrides[require_teacher] = lambda: STRANGER
    forbidden = client.get(f"/teaching-packs/media-asset-versions/{asset_id}")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "not_media_asset_owner"

    client.app.dependency_overrides[require_teacher] = lambda: OWNER


def test_non_image_upload_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/teaching-packs/media-asset-versions",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
        data={"scope": "private_teacher"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "image_uploads_only"


def test_teacher_cannot_create_a_system_scoped_asset(client: TestClient) -> None:
    response = client.post(
        "/teaching-packs/media-asset-versions",
        files={"file": ("cell.png", b"bytes", "image/png")},
        data={"scope": "system"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "scope_requires_higher_authority"


def test_visual_source_suggestion_convert_never_fetches_the_candidate_url(client: TestClient) -> None:
    run_id, _ = anyio.run(_seed_run_with_document, "infographic-router-3")

    suggested = client.post(
        f"/teaching-packs/runs/{run_id}/visual-source-suggestions",
        json={
            "description": "A labeled diagram of mitosis stages.",
            "candidate_url": "https://example.com/mitosis.png",
            "license_hint": "CC-BY-4.0, attribution required",
        },
    )
    assert suggested.status_code == 201
    suggestion_id = suggested.json()["suggestion_id"]
    assert suggested.json()["status"] == "pending"

    uploaded = _upload(client, filename="mitosis-licensed.png")

    converted = client.post(
        f"/teaching-packs/visual-source-suggestions/{suggestion_id}/convert",
        json={"asset_id": uploaded["asset_id"]},
    )
    assert converted.status_code == 200
    assert converted.json()["status"] == "converted"
    assert converted.json()["converted_asset_id"] == uploaded["asset_id"]

    listed = client.get(f"/teaching-packs/runs/{run_id}/visual-source-suggestions")
    assert listed.status_code == 200
    assert listed.json()["suggestions"][0]["status"] == "converted"

    already_converted = client.post(
        f"/teaching-packs/visual-source-suggestions/{suggestion_id}/convert",
        json={"asset_id": uploaded["asset_id"]},
    )
    assert already_converted.status_code == 409

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
