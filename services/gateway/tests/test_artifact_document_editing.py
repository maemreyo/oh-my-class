"""#431: registry-driven V2 editing, restore, review notes, approval, delegation."""

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
from services.gateway.artifact_approval_service import (
    ArtifactNotCurrentError,
    BlockingReviewNotesOpenError,
    approve_all_current,
    approve_artifact_version,
)
from services.gateway.artifact_document_edit_service import (
    ArtifactVersionNotFoundError,
    edit_artifact_document,
    restore_artifact_document,
)
from services.gateway.artifact_document_models import ContentDependencyRecord
from services.gateway.artifact_document_store import (
    ArtifactDocumentStore,
    ArtifactDocumentWrite,
    ContentDependencyCreate,
)
from services.gateway.auth.models import Role, User
from services.gateway.auth.ownership import check_run_owner, check_run_reviewer
from services.gateway.models import Base
from services.gateway.review_note_store import ReviewNoteCreate, ReviewNoteStore
from services.gateway.run_delegation_store import RunDelegationStore
from services.gateway.teaching_pack_snapshot_errors import StaleArtifactVersionError
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


def _block_document(
    document_id: str,
    *,
    artifact_id: str,
    version: int,
    text: str = "Original text",
    parent_document_id: str | None = None,
    source_document_id: str | None = None,
) -> ArtifactDocument:
    return ArtifactDocument(
        document_id=document_id,
        artifact_id=artifact_id,
        artifact_type="recap",
        version=version,
        language="en",
        audience="student",
        authority="generated" if version == 1 else "teacher_edit",
        parent_document_id=parent_document_id,
        source_document_id=source_document_id,
        payload=ArtifactPayload(
            payload_kind="block_document",
            sections=[DocumentSection(
                entity_id="section-1",
                title="Recap",
                blocks=[DocumentBlock(entity_id="block-1", block_kind="paragraph", text=text)],
            )],
        ),
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


async def _seed_run_and_v1_document(session: AsyncSession, *, artifact_id: str) -> RunId:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-editing"),
        raw_request="Build a recap",
        class_info={"grade": 5},
    ))
    document = _block_document(f"document-{uuid4()}", artifact_id=artifact_id, version=1)
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=run_id, document=document))
    return run_id


async def test_edit_creates_next_version_and_surfaces_dependency_impact(session: AsyncSession) -> None:
    artifact_id = "recap-1"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)
    v1 = await ArtifactDocumentStore(session).get_latest(run_id, artifact_id)
    assert v1 is not None

    # a derived artifact declares a dependency on v1 -- editing v1 must surface it as impacted.
    dependent = _block_document(f"document-{uuid4()}", artifact_id="quiz-derived", version=1)
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=dependent,
        dependencies=[],
    ))
    session.add(ContentDependencyRecord(
        document_id=dependent.document_id, source_document_id=v1.document_id, dependency_kind="answer_projection",
    ))
    await session.flush()

    outcome = await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id=artifact_id,
        base_version=1,
        payload=_block_document(
            "ignored", artifact_id=artifact_id, version=1, text="Edited text",
        ).payload,
        authority="teacher_edit",
    )

    assert outcome.document.version == 2
    assert outcome.document.authority == "teacher_edit"
    assert outcome.document.parent_document_id == v1.document_id
    assert outcome.document.payload.sections[0].blocks[0].text == "Edited text"
    assert outcome.impacted_artifact_ids == ["quiz-derived"]


async def test_quiz_edit_marks_derived_answer_key_dependency_impacted(session: AsyncSession) -> None:
    run_id = await _seed_run_and_v1_document(session, artifact_id="quiz-answers")
    source = await ArtifactDocumentStore(session).get_latest(run_id, "quiz-answers")
    assert source is not None
    answer_key = _block_document(f"document-{uuid4()}", artifact_id="answer-key-1", version=1)
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=answer_key,
        dependencies=[ContentDependencyCreate(
            source_document_id=source.document_id,
            dependency_kind="answer_projection",
        )],
    ))

    outcome = await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id="quiz-answers",
        base_version=1,
        payload=_block_document("ignored", artifact_id="quiz-answers", version=1, text="Edited question").payload,
        authority="teacher_edit",
    )

    assert outcome.document.version == 2
    assert outcome.impacted_artifact_ids == ["answer-key-1"]


async def test_edit_with_stale_base_version_raises_actionable_conflict(session: AsyncSession) -> None:
    artifact_id = "recap-2"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)
    await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id=artifact_id,
        base_version=1,
        payload=_block_document(
            "ignored", artifact_id=artifact_id, version=1, text="First edit",
        ).payload,
        authority="teacher_edit",
    )

    with pytest.raises(StaleArtifactVersionError) as excinfo:
        await edit_artifact_document(
            session,
            run_id=run_id,
            artifact_id=artifact_id,
            base_version=1,  # stale -- the artifact is already at version 2
            payload=_block_document(
                "ignored", artifact_id=artifact_id, version=1, text="Racing edit",
            ).payload,
            authority="teacher_edit",
        )

    assert excinfo.value.base_version == 1
    assert excinfo.value.current_version == 2


async def test_restore_creates_new_version_without_mutating_history(session: AsyncSession) -> None:
    artifact_id = "recap-3"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)
    await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id=artifact_id,
        base_version=1,
        payload=_block_document(
            "ignored", artifact_id=artifact_id, version=1, text="Changed text",
        ).payload,
        authority="teacher_edit",
    )

    outcome = await restore_artifact_document(session, run_id=run_id, artifact_id=artifact_id, target_version=1)

    versions = await ArtifactDocumentStore(session).list_versions(run_id, artifact_id)
    assert [v.version for v in versions] == [3, 2, 1]
    assert outcome.document.version == 3
    assert outcome.document.authority == "restored"
    assert outcome.document.payload.sections[0].blocks[0].text == "Original text"


async def test_restore_unknown_version_raises_not_found(session: AsyncSession) -> None:
    artifact_id = "recap-4"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)

    with pytest.raises(ArtifactVersionNotFoundError):
        await restore_artifact_document(session, run_id=run_id, artifact_id=artifact_id, target_version=99)


async def test_blocking_review_note_prevents_approval_until_resolved(session: AsyncSession) -> None:
    artifact_id = "recap-5"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)
    latest = await ArtifactDocumentStore(session).get_latest(run_id, artifact_id)
    assert latest is not None

    note_store = ReviewNoteStore(session)
    note = await note_store.create(ReviewNoteCreate(
        note_id=f"note-{uuid4()}",
        run_id=run_id,
        artifact_id=artifact_id,
        document_id=latest.document_id,
        author_id="reviewer-1",
        body="This example is confusing for grade 5.",
        blocking=True,
    ))

    with pytest.raises(BlockingReviewNotesOpenError):
        await approve_artifact_version(
            session, run_id=run_id, artifact_id=artifact_id, version=1, approver_id="teacher-editing",
        )

    await note_store.resolve(note.note_id)
    await approve_artifact_version(
        session, run_id=run_id, artifact_id=artifact_id, version=1, approver_id="teacher-editing",
    )  # no longer raises


async def test_approve_version_that_is_not_current_raises(session: AsyncSession) -> None:
    artifact_id = "recap-6"
    run_id = await _seed_run_and_v1_document(session, artifact_id=artifact_id)
    await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id=artifact_id,
        base_version=1,
        payload=_block_document(
            "ignored", artifact_id=artifact_id, version=1, text="v2 text",
        ).payload,
        authority="teacher_edit",
    )

    with pytest.raises(ArtifactNotCurrentError) as excinfo:
        await approve_artifact_version(
            session, run_id=run_id, artifact_id=artifact_id, version=1, approver_id="teacher-editing",
        )
    assert excinfo.value.current_version == 2


async def test_approve_all_current_reports_blocked_artifacts_separately(session: AsyncSession) -> None:
    run_id = await _seed_run_and_v1_document(session, artifact_id="recap-clean")
    document = _block_document(f"document-{uuid4()}", artifact_id="recap-blocked", version=1)
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=run_id, document=document))
    await ReviewNoteStore(session).create(ReviewNoteCreate(
        note_id=f"note-{uuid4()}",
        run_id=run_id,
        artifact_id="recap-blocked",
        document_id=document.document_id,
        author_id="reviewer-1",
        body="Needs a fix before approval.",
        blocking=True,
    ))

    result = await approve_all_current(
        session,
        run_id=run_id,
        artifact_ids=["recap-clean", "recap-blocked", "does-not-exist"],
        approver_id="teacher-editing",
    )

    assert result.approved == ["recap-clean"]
    assert {b["artifact_id"]: b["reason"] for b in result.blocked} == {
        "recap-blocked": "blocking_review_note",
        "does-not-exist": "no_version",
    }


async def test_delegate_may_review_but_not_own_the_run(session: AsyncSession) -> None:
    run_id = await _seed_run_and_v1_document(session, artifact_id="recap-delegation")
    owner = User(user_id="teacher-editing", username="teacher-editing", role=Role.TEACHER)
    stranger = User(user_id="teacher-stranger", username="teacher-stranger", role=Role.TEACHER)

    assert await check_run_owner(run_id, stranger, session) is False
    assert await check_run_reviewer(run_id, stranger, session) is False

    await RunDelegationStore(session).grant(run_id, stranger.user_id, granted_by=owner.user_id)

    assert await check_run_reviewer(run_id, stranger, session) is True, "delegate can review"
    assert await check_run_owner(run_id, stranger, session) is False, "delegate does not gain full ownership"
