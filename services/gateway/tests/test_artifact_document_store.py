from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.answer_set import AnswerEntry, AnswerSet
from common.contracts.artifact import ArtifactContent
from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult
from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    AssessmentOption,
    AssessmentQuestion,
)
from services.gateway.artifact_document_store import (
    ArtifactDocumentStore,
    ArtifactDocumentWrite,
    ContentApprovalCreate,
    ContentDependencyCreate,
    ContentVariantCreate,
)
from services.gateway.artifact_document_content_store import GatewayArtifactDocumentContentStore
from services.gateway.models import Base
from services.gateway.artifact_document_models import ArtifactDocumentRecord, AnswerSetRecord
from services.gateway.teaching_pack_models import RunEvent
from services.gateway.teaching_pack_snapshot_schemas import ArtifactSnapshotCreate
from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


def _assessment_document(
    document_id: str,
    *,
    version: int,
    parent_document_id: str | None = None,
    source_document_id: str | None = None,
) -> ArtifactDocument:
    return ArtifactDocument(
        document_id=document_id,
        artifact_id="quiz-1",
        artifact_type="quiz",
        version=version,
        language="en",
        audience="student",
        authority="generated" if version == 1 else "teacher_edit",
        parent_document_id=parent_document_id,
        source_document_id=source_document_id,
        payload=ArtifactPayload(
            payload_kind="assessment_document",
            questions=[
                AssessmentQuestion(
                    entity_id="question-1",
                    prompt="Which fraction equals one half?",
                    options=[
                        AssessmentOption(entity_id="option-a", text="1/4"),
                        AssessmentOption(entity_id="option-b", text="2/4"),
                    ],
                ),
            ],
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


async def test_persists_immutable_v2_lineage_and_reads_legacy_preview(
    session: AsyncSession,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-lineage"),
        raw_request="Build a fractions quiz",
        class_info={"grade": 5},
    ))
    snapshot_id = f"snapshot-{uuid4()}"
    await TeachingPackSnapshotStore(session).create_snapshot(ArtifactSnapshotCreate(
        snapshot_id=snapshot_id,
        run_id=run_id,
        artifact_id="quiz-1",
        artifact_type="quiz",
        content_json={"title": "Fractions"},
        rendered_html="<!DOCTYPE html><html><body>oh-my-class</body></html>",
        renderer_version="test-renderer@1",
    ))

    document = _assessment_document(f"document-{uuid4()}", version=1)
    answers = AnswerSet(
        answer_set_id=f"answers-{uuid4()}",
        source_document_id=document.document_id,
        source_version=document.version,
        entries=[AnswerEntry(
            entity_id="answer-1",
            question_id="question-1",
            correct_option_ids=["option-b"],
        )],
    )
    store = ArtifactDocumentStore(session)

    persisted = await store.persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=document,
        answer_set=answers,
        snapshot_id=snapshot_id,
        approval=ContentApprovalCreate(
            approval_id=f"approval-{uuid4()}",
            status="approved",
            approved_by="teacher-lineage",
        ),
    ))
    duplicate = await store.persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=document,
        answer_set=answers.model_copy(update={"answer_set_id": f"answers-{uuid4()}"}),
        snapshot_id=snapshot_id,
        approval=ContentApprovalCreate(
            approval_id=f"approval-{uuid4()}",
            status="approved",
            approved_by="teacher-lineage",
        ),
    ))
    derived = _assessment_document(
        f"document-{uuid4()}",
        version=2,
        parent_document_id=document.document_id,
        source_document_id=document.document_id,
    )
    await store.persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=derived,
        variant=ContentVariantCreate(
            variant_id=f"variant-{uuid4()}",
            variant_kind="language_scaffold",
            source_document_id=document.document_id,
        ),
        dependencies=[ContentDependencyCreate(
            source_document_id=document.document_id,
            dependency_kind="answer_projection",
        )],
    ))
    await store.persist(ArtifactDocumentWrite(
        run_id=run_id,
        document=derived,
        variant=ContentVariantCreate(
            variant_id=f"variant-{uuid4()}",
            variant_kind="language_scaffold",
            source_document_id=document.document_id,
        ),
    ))
    v2_preview = await store.get_preview_source(run_id, document.document_id, snapshot_id)
    v1_preview = await store.get_preview_source(run_id, "missing-document", snapshot_id)

    assert persisted.document == document
    assert duplicate == persisted
    assert persisted.answer_set == answers
    assert persisted.approval_status == "approved"
    assert v2_preview.schema_version == "v2"
    assert v2_preview.snapshot_id == snapshot_id
    assert v2_preview.legacy is False
    assert v1_preview.schema_version == "v1"
    assert v1_preview.snapshot_id == snapshot_id
    assert v1_preview.legacy is True

    events = list((await session.execute(
        select(RunEvent).where(RunEvent.run_id == run_id),
    )).scalars())
    legacy_events = [event for event in events if event.event_name == "artifact_document_legacy_read"]
    assert len(legacy_events) == 1
    assert legacy_events[0].payload["payload"]["document_id"] == "missing-document"
    assert legacy_events[0].payload["payload"]["snapshot_id"] == snapshot_id


async def test_gateway_adapter_persists_v2_document_and_separate_answer_set(
    session: AsyncSession,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-v2-adapter"),
        raw_request="Build a fractions quiz",
        class_info={"grade": 5},
    ))
    await session.commit()
    session_factory = async_sessionmaker(bind=session.bind, expire_on_commit=False)
    adapter = GatewayArtifactDocumentContentStore(session_factory)
    artifact = ArtifactContent(
        artifact_type="quiz",
        theme="default",
        title="Fractions quiz",
        sections=[{"components": [{
            "type": "question_card",
            "id": "question-1",
            "text": "Which fraction equals one half?",
            "options": {"A": "1/4", "B": "2/4"},
            "answer": "B",
            "explain": "Two fourths equals one half.",
        }]}],
        metadata={"answer_set": {"must_not_persist": True}},
        accessibility={"language": "en"},
    )
    answers = AnswerSet(
        answer_set_id="answers-pending",
        source_document_id="pending",
        source_version=1,
        entries=[AnswerEntry(
            entity_id="answer-question-1",
            question_id="question-1",
            correct_option_ids=["B"],
        )],
    )

    reference = await adapter.persist_result(
        str(run_id),
        "generation-1",
        ArtifactPersistenceResult(artifact=artifact, answer_set=answers),
        "quiz-1",
    )
    async with session_factory() as verification_session:
        persisted = await ArtifactDocumentStore(verification_session).get_persisted(reference.document_id)

    assert persisted.answer_set is not None
    assert persisted.answer_set.source_document_id == reference.document_id
    assert "answer_set" not in persisted.document.model_dump(mode="json")
    assert "answer" not in persisted.document.model_dump(mode="json")


async def test_gateway_adapter_rolls_back_document_when_answer_set_insert_fails(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-v2-rollback"),
        raw_request="Build a fractions quiz",
        class_info={"grade": 5},
    ))
    await session.commit()
    session_factory = async_sessionmaker(bind=session.bind, expire_on_commit=False)
    adapter = GatewayArtifactDocumentContentStore(session_factory)
    artifact = ArtifactContent(
        artifact_type="quiz",
        theme="default",
        title="Fractions quiz",
        sections=[{"components": [{
            "type": "question_card",
            "id": "question-1",
            "text": "Which fraction equals one half?",
            "options": {"A": "1/4", "B": "2/4"},
            "answer": "B",
            "explain": "Two fourths equals one half.",
        }]}],
        metadata={},
        accessibility={"language": "en"},
    )
    answers = AnswerSet(
        answer_set_id="answers-pending",
        source_document_id="pending",
        source_version=1,
        entries=[AnswerEntry(
            entity_id="answer-question-1",
            question_id="question-1",
            correct_option_ids=["B"],
        )],
    )

    async def fail_answer_insert(_store: ArtifactDocumentStore, _answer_set: AnswerSet) -> None:
        raise RuntimeError("injected answer-set failure")

    monkeypatch.setattr(ArtifactDocumentStore, "_insert_answer_set", fail_answer_insert)

    with pytest.raises(RuntimeError, match="injected answer-set failure"):
        await adapter.persist_result(
            str(run_id),
            "generation-rollback",
            ArtifactPersistenceResult(artifact=artifact, answer_set=answers),
            "quiz-1",
        )

    async with session_factory() as verification_session:
        documents = list((await verification_session.execute(
            select(ArtifactDocumentRecord).where(ArtifactDocumentRecord.run_id == run_id),
        )).scalars())
        answer_sets = list((await verification_session.execute(
            select(AnswerSetRecord).where(
                AnswerSetRecord.source_document_id == "generation-rollback:quiz-1",
            ),
        )).scalars())

    assert documents == []
    assert answer_sets == []
