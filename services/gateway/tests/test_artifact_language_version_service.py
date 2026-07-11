"""#451: Language Versions and typed Content Variants.

Covers the acceptance criteria directly: translation is an independently
approvable, source-linked lineage; required variant kinds (accessibility
always, language_scaffold when target_language != instruction_language)
auto-generate while every other kind stays a recommendation; re-deriving
extends the existing derived lineage instead of forking a new one each time.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    DocumentBlock,
    DocumentSection,
)
from services.gateway.artifact_approval_service import approve_artifact_version
from services.gateway.artifact_document_edit_service import ArtifactHasNoVersionsError, edit_artifact_document
from services.gateway.artifact_document_models import ContentApprovalRecord
from services.gateway.artifact_document_store import ArtifactDocumentStore, ArtifactDocumentWrite
from services.gateway.artifact_language_version_service import (
    LanguageVersionAlreadyInTargetLanguageError,
    create_content_variant,
    create_language_version,
    ensure_required_variants,
    required_variant_kinds,
)
from services.gateway.models import Base
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


def _block_document(
    document_id: str, *, artifact_id: str, version: int = 1, text: str = "Original text",
) -> ArtifactDocument:
    return ArtifactDocument(
        document_id=document_id,
        artifact_id=artifact_id,
        artifact_type="recap",
        version=version,
        language="en",
        audience="student",
        authority="generated",
        payload=ArtifactPayload(
            payload_kind="block_document",
            sections=[DocumentSection(
                entity_id="section-1",
                title="Recap",
                blocks=[DocumentBlock(entity_id="block-1", block_kind="paragraph", text=text)],
            )],
        ),
    )


def _payload(text: str) -> ArtifactPayload:
    return ArtifactPayload(
        payload_kind="block_document",
        sections=[DocumentSection(
            entity_id="section-1",
            title="Recap",
            blocks=[DocumentBlock(entity_id="block-1", block_kind="paragraph", text=text)],
        )],
    )


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


async def _seed_run_with_source(session: AsyncSession, artifact_id: str) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id, teacher_id=TeacherId("teacher-lang-version"),
        raw_request="Build a recap", class_info={"grade": 5},
    ))
    document = _block_document(f"document-{uuid4()}", artifact_id=artifact_id)
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=run_id, document=document))
    return run_id


async def test_translation_gets_its_own_artifact_id_and_independent_approval(session: AsyncSession) -> None:
    artifact_id = "recap-1"
    run_id = await _seed_run_with_source(session, artifact_id)

    outcome = await create_language_version(
        session, run_id=run_id, source_artifact_id=artifact_id,
        target_language="vi", payload=_payload("Văn bản tiếng Việt"),
    )
    assert outcome.document.artifact_id != artifact_id
    assert outcome.document.version == 1
    assert outcome.document.language == "vi"
    assert outcome.document.authority == "translated"
    assert outcome.document.source_document_id is not None

    await approve_artifact_version(
        session, run_id=run_id, artifact_id=outcome.document.artifact_id, version=1, approver_id="teacher-1",
    )
    store = ArtifactDocumentStore(session)
    translated_latest = await store.get_latest(run_id, outcome.document.artifact_id)
    source_latest = await store.get_latest(run_id, artifact_id)
    assert translated_latest is not None
    assert source_latest is not None
    approval_statement = select(ContentApprovalRecord.document_id, ContentApprovalRecord.status)
    approvals = dict((await session.execute(approval_statement)).all())
    assert approvals.get(translated_latest.document_id) == "approved"
    assert source_latest.document_id not in approvals


async def test_translating_into_the_current_language_is_rejected(session: AsyncSession) -> None:
    artifact_id = "recap-2"
    run_id = await _seed_run_with_source(session, artifact_id)
    with pytest.raises(LanguageVersionAlreadyInTargetLanguageError):
        await create_language_version(
            session, run_id=run_id, source_artifact_id=artifact_id,
            target_language="en", payload=_payload("Still English"),
        )


async def test_translating_a_never_persisted_artifact_raises(session: AsyncSession) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id, teacher_id=TeacherId("teacher-lang-version"),
        raw_request="Build a recap", class_info={"grade": 5},
    ))
    with pytest.raises(ArtifactHasNoVersionsError):
        await create_language_version(
            session, run_id=run_id, source_artifact_id="never-existed",
            target_language="vi", payload=_payload("x"),
        )


async def test_retranslating_extends_the_existing_lineage_and_repoints_to_the_newer_source(
    session: AsyncSession,
) -> None:
    artifact_id = "recap-3"
    run_id = await _seed_run_with_source(session, artifact_id)

    first = await create_language_version(
        session, run_id=run_id, source_artifact_id=artifact_id,
        target_language="vi", payload=_payload("Bản dịch đầu tiên"),
    )
    await edit_artifact_document(
        session, run_id=run_id, artifact_id=artifact_id,
        base_version=1, payload=_payload("Updated English source"), authority="teacher_edit",
    )
    second = await create_language_version(
        session, run_id=run_id, source_artifact_id=artifact_id,
        target_language="vi", payload=_payload("Bản dịch cập nhật"),
    )

    assert second.document.artifact_id == first.document.artifact_id
    assert second.document.version == 2
    assert second.document.parent_document_id == first.document.document_id
    updated_source = await ArtifactDocumentStore(session).get_latest(run_id, artifact_id)
    assert second.document.source_document_id == updated_source.document_id
    assert second.document.source_document_id != first.document.source_document_id


async def test_content_variant_registers_variant_kind_and_dependency_edge(session: AsyncSession) -> None:
    artifact_id = "recap-4"
    run_id = await _seed_run_with_source(session, artifact_id)

    outcome = await create_content_variant(
        session, run_id=run_id, source_artifact_id=artifact_id,
        variant_kind="accessibility", payload=_payload("Simplified accessible text"),
    )
    assert outcome.document.artifact_id != artifact_id
    assert outcome.document.language == "en"  # variants keep the source language, unlike translations

    edit_outcome = await edit_artifact_document(
        session, run_id=run_id, artifact_id=artifact_id,
        base_version=1, payload=_payload("Edited source"), authority="teacher_edit",
    )
    assert outcome.document.artifact_id in edit_outcome.impacted_artifact_ids


def test_required_variant_kinds_always_requires_accessibility() -> None:
    assert "accessibility" in required_variant_kinds({})
    assert "accessibility" in required_variant_kinds({"target_language": "en", "instruction_language": "en"})


def test_required_variant_kinds_requires_language_scaffold_only_when_languages_differ() -> None:
    same_language = required_variant_kinds({"target_language": "en", "instruction_language": "en"})
    different_language = required_variant_kinds({"target_language": "en", "instruction_language": "vi"})
    assert "language_scaffold" not in same_language
    assert "language_scaffold" in different_language


async def test_ensure_required_variants_creates_required_reports_missing_payload_and_recommends_the_rest(
    session: AsyncSession,
) -> None:
    artifact_id = "recap-5"
    run_id = await _seed_run_with_source(session, artifact_id)

    result = await ensure_required_variants(
        session, run_id=run_id, source_artifact_id=artifact_id,
        class_profile={"target_language": "en", "instruction_language": "vi"},
        payload_by_kind={"accessibility": _payload("Accessible text")},
    )
    assert result.created == ["accessibility"]
    assert result.missing_payload == ["language_scaffold"]
    assert "semantic_support" in result.recommended
    assert "challenge" in result.recommended
    assert "accessibility" not in result.recommended
    assert "language_scaffold" not in result.recommended


async def test_ensure_required_variants_does_not_recreate_an_already_present_variant(
    session: AsyncSession,
) -> None:
    artifact_id = "recap-6"
    run_id = await _seed_run_with_source(session, artifact_id)
    class_profile = {"target_language": "en", "instruction_language": "en"}

    first = await ensure_required_variants(
        session, run_id=run_id, source_artifact_id=artifact_id,
        class_profile=class_profile, payload_by_kind={"accessibility": _payload("v1")},
    )
    second = await ensure_required_variants(
        session, run_id=run_id, source_artifact_id=artifact_id,
        class_profile=class_profile, payload_by_kind={"accessibility": _payload("v2")},
    )
    assert first.created == ["accessibility"]
    assert second.created == []
    assert second.already_present == ["accessibility"]
