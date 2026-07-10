"""#431: the edit/restore/notes/approval/delegation surfaces through real HTTP."""

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
from services.gateway.routers.artifact_documents import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(user_id="teacher-router-owner", username="teacher-router-owner", role=Role.TEACHER)


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

    app.dependency_overrides[require_teacher] = lambda: OWNER
    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _seed_run_with_document(artifact_id: str) -> str:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    run_id = f"test-{uuid4()}"
    document_id = f"document-{uuid4()}"
    async with session_factory() as session:
        await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
            run_id=RunId(run_id),
            teacher_id=TeacherId(OWNER.user_id),
            raw_request="Build a recap",
            class_info={"grade": 5},
        ))
        document = ArtifactDocument(
            document_id=document_id,
            artifact_id=artifact_id,
            artifact_type="recap",
            version=1,
            language="en",
            audience="student",
            authority="generated",
            payload=ArtifactPayload(
                payload_kind="block_document",
                sections=[DocumentSection(
                    entity_id="section-1",
                    title="Recap",
                    blocks=[DocumentBlock(entity_id="block-1", block_kind="paragraph", text="Original text")],
                )],
            ),
        )
        await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=RunId(run_id), document=document))
        await session.commit()
    await engine.dispose()
    return run_id


def _payload_for(text: str) -> dict[str, object]:
    return {
        "payload_kind": "block_document",
        "sections": [{
            "entity_id": "section-1",
            "title": "Recap",
            "blocks": [{"entity_id": "block-1", "block_kind": "paragraph", "text": text}],
        }],
    }


def test_edit_conflict_is_actionable_and_approval_is_blocked_by_open_note(client: TestClient) -> None:
    artifact_id = "recap-router-1"
    run_id = anyio.run(_seed_run_with_document, artifact_id)

    edited = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/edit",
        json={"base_version": 1, "payload": _payload_for("Edited text"), "authority": "teacher_edit"},
    )
    assert edited.status_code == 200
    assert edited.json()["document"]["version"] == 2
    assert edited.json()["impacted_artifact_ids"] == []

    stale_edit = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/edit",
        json={"base_version": 1, "payload": _payload_for("Racing edit"), "authority": "teacher_edit"},
    )
    assert stale_edit.status_code == 409
    assert stale_edit.json()["detail"] == {
        "error": "base_version_stale", "base_version": 1, "current_version": 2,
    }

    versions = client.get(f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/versions")
    assert [v["version"] for v in versions.json()] == [2, 1]

    note = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/notes",
        json={"body": "Please double check the example.", "blocking": True},
    )
    assert note.status_code == 201

    blocked_approval = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/approve",
        json={"version": 2},
    )
    assert blocked_approval.status_code == 409
    assert blocked_approval.json()["detail"] == "blocking_review_note_open"

    resolved = client.post(f"/teaching-packs/runs/{run_id}/notes/{note.json()['note_id']}/resolve")
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    approval = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/approve",
        json={"version": 2},
    )
    assert approval.status_code == 204

    anyio.run(_delete_created, run_id)


def test_only_owner_may_delegate_but_delegate_can_approve(client: TestClient) -> None:
    artifact_id = "recap-router-2"
    run_id = anyio.run(_seed_run_with_document, artifact_id)
    delegate = User(user_id="teacher-router-delegate", username="teacher-router-delegate", role=Role.TEACHER)

    client.app.dependency_overrides[require_teacher] = lambda: delegate
    forbidden = client.post(f"/teaching-packs/runs/{run_id}/delegate", json={"delegate_id": delegate.user_id})
    assert forbidden.status_code == 404, "non-owners get 404, not 403 -- matches get_run_with_ownership elsewhere"

    client.app.dependency_overrides[require_teacher] = lambda: OWNER
    granted = client.post(f"/teaching-packs/runs/{run_id}/delegate", json={"delegate_id": delegate.user_id})
    assert granted.status_code == 201

    client.app.dependency_overrides[require_teacher] = lambda: delegate
    approval = client.post(
        f"/teaching-packs/runs/{run_id}/artifacts/{artifact_id}/approve",
        json={"version": 1},
    )
    assert approval.status_code == 204

    client.app.dependency_overrides[require_teacher] = lambda: OWNER
    anyio.run(_delete_created, run_id)


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda _: set(Base.metadata.tables))
        if "public.artifact_review_notes" not in existing_tables or "public.run_delegations" not in existing_tables:
            pytest.skip("review-notes/delegation tables are not present -- run alembic upgrade head")
    await engine.dispose()


async def _delete_created(run_id: str) -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
    await engine.dispose()
