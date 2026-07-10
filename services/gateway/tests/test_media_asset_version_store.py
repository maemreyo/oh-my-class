"""#434: immutable media asset versioning, dependency impact, deletion, checksum integrity."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    DocumentBlock,
    DocumentSection,
)
from services.gateway.artifact_document_store import ArtifactDocumentStore, ArtifactDocumentWrite
from services.gateway.media_asset_version_store import (
    ChecksumMismatchError,
    MediaAssetHasDependentsError,
    MediaAssetNotFoundError,
    MediaAssetVersionStore,
)
from services.gateway.models import Base
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def _seed_run_and_document(session: AsyncSession) -> str:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-media"),
        raw_request="Build an infographic",
        class_info={"grade": 5},
    ))
    document = ArtifactDocument(
        document_id=f"document-{uuid4()}",
        artifact_id="infographic-1",
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
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=run_id, document=document))
    return document.document_id


async def test_replace_creates_a_new_version_and_surfaces_dependency_impact(session: AsyncSession) -> None:
    document_id = await _seed_run_and_document(session)
    store = MediaAssetVersionStore(session)
    v1 = await store.create(
        asset_id="media-1",
        owner_scope="private_teacher",
        owner_id="teacher-media",
        filename="cell.png",
        content_type="image/png",
        storage_key="teacher-media/teacher-media/media-1.png",
        content=b"original-bytes",
        alt_text="A labeled diagram of a plant cell.",
    )
    await store.record_dependency(v1.version_id, document_id)

    v2, impacted = await store.replace(
        "media-1",
        filename="cell-v2.png",
        content_type="image/png",
        storage_key="teacher-media/teacher-media/media-1.png",
        content=b"updated-bytes",
        alt_text="An updated labeled diagram of a plant cell.",
    )

    assert v2.version == 2
    assert v2.parent_version_id == v1.version_id
    assert v2.owner_id == v1.owner_id  # lineage carries ownership forward
    assert impacted == [document_id]
    assert v2.checksum_sha256 != v1.checksum_sha256

    latest = await store.get_latest("media-1")
    assert latest is not None
    assert latest.version_id == v2.version_id
    versions = await store.list_versions("media-1")
    assert [v.version for v in versions] == [2, 1]


async def test_replace_unknown_asset_raises_not_found(session: AsyncSession) -> None:
    store = MediaAssetVersionStore(session)

    with pytest.raises(MediaAssetNotFoundError):
        await store.replace(
            "does-not-exist",
            filename="x.png",
            content_type="image/png",
            storage_key="x",
            content=b"x",
        )


async def test_delete_is_blocked_while_dependents_exist(session: AsyncSession) -> None:
    document_id = await _seed_run_and_document(session)
    store = MediaAssetVersionStore(session)
    version = await store.create(
        asset_id="media-2",
        owner_scope="private_teacher",
        owner_id="teacher-media",
        filename="cell.png",
        content_type="image/png",
        storage_key="teacher-media/teacher-media/media-2.png",
        content=b"bytes",
    )
    await store.record_dependency(version.version_id, document_id)

    with pytest.raises(MediaAssetHasDependentsError) as excinfo:
        await store.soft_delete("media-2")
    assert excinfo.value.dependent_document_ids == [document_id]

    assert await store.get_latest("media-2") is not None  # not deleted


async def test_delete_succeeds_once_no_dependents_remain(session: AsyncSession) -> None:
    store = MediaAssetVersionStore(session)
    await store.create(
        asset_id="media-3",
        owner_scope="private_teacher",
        owner_id="teacher-media",
        filename="cell.png",
        content_type="image/png",
        storage_key="teacher-media/teacher-media/media-3.png",
        content=b"bytes",
    )

    await store.soft_delete("media-3")

    assert await store.get_latest("media-3") is None


async def test_checksum_mismatch_is_detected_before_serving_bytes(session: AsyncSession) -> None:
    store = MediaAssetVersionStore(session)
    version = await store.create(
        asset_id="media-4",
        owner_scope="private_teacher",
        owner_id="teacher-media",
        filename="cell.png",
        content_type="image/png",
        storage_key="teacher-media/teacher-media/media-4.png",
        content=b"original-bytes",
    )

    await store.verify_checksum(version.version_id, b"original-bytes")  # must not raise
    with pytest.raises(ChecksumMismatchError):
        await store.verify_checksum(version.version_id, b"tampered-bytes")
