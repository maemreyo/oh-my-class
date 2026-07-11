from __future__ import annotations

import pytest

from common.contracts.artifact import ArtifactContent
from common.contracts.answer_set import AnswerEntry, AnswerSet
from packages.agents.teaching_pack.content_orchestrator import (
    ArtifactPersistenceResult,
    ArtifactDocumentReference,
    InMemoryArtifactContentStore,
    SpecialistResult,
)
from packages.agents.teaching_pack.reducers import current_generation_artifact_references


def _artifact() -> ArtifactContent:
    return ArtifactContent(
        artifact_id="lesson-1",
        artifact_type="lesson",
        theme="default",
        title="Fractions lesson",
        sections=[{"title": "Introduction", "content": "A fraction names equal parts."}],
        metadata={},
        accessibility={"language": "en"},
    )


@pytest.mark.anyio
async def test_content_store_returns_reference_without_payload() -> None:
    store = InMemoryArtifactContentStore()

    reference = await store.persist("run-1", "run-1:artifact:1", _artifact(), "lesson-1")

    assert reference == ArtifactDocumentReference(
        document_id="run-1:artifact:1:lesson-1",
        artifact_id="lesson-1",
        artifact_type="lesson",
        generation_id="run-1:artifact:1",
        version=1,
        title="Fractions lesson",
    )
    assert "sections" not in reference.as_state()
    assert await store.read_projection(reference.document_id) == _artifact()


@pytest.mark.anyio
async def test_content_store_removes_teacher_only_answer_data_from_assessment_projections() -> None:
    artifact = ArtifactContent(
        artifact_id="quiz-1",
        artifact_type="quiz",
        theme="default",
        title="Fractions quiz",
        sections=[{"components": [{
            "type": "question_card",
            "id": "question-1",
            "text": "Which fraction is one half?",
            "options": {"A": "2/4", "B": "1/3"},
            "answer": "A",
            "explain": "Two fourths equals one half.",
        }]}],
        metadata={"answer_set": {"teacher_only": True}},
        accessibility={"language": "en"},
    )
    store = InMemoryArtifactContentStore()

    reference = await store.persist_result(
        "run-1",
        "gen-1",
        ArtifactPersistenceResult(artifact=artifact),
        "quiz-1",
    )
    persisted = await store.read_projection(reference.document_id)

    component = persisted.sections[0]["components"][0]
    assert "answer_set" not in persisted.metadata
    assert "answer" not in component
    assert "explain" not in component

    answer_set = AnswerSet(
        answer_set_id="answers-pending",
        source_document_id="pending",
        source_version=1,
        entries=[AnswerEntry(entity_id="answer-question-1", question_id="question-1", correct_option_ids=["A"])],
    )
    reference = await store.persist_result(
        "run-1",
        "gen-2",
        ArtifactPersistenceResult(artifact=artifact, answer_set=answer_set),
        "quiz-2",
    )

    assert (await store.read_answer_set(reference.document_id)).entries[0].correct_option_ids == ["A"]


def test_current_generation_references_exclude_stale_cycle_results() -> None:
    references = [
        ArtifactDocumentReference(
            document_id="run-1:artifact:1:lesson-1",
            artifact_id="lesson-1",
            artifact_type="lesson",
            generation_id="run-1:artifact:1",
            version=1,
            title="Old lesson",
        ).as_state(),
        ArtifactDocumentReference(
            document_id="run-1:artifact:2:lesson-1",
            artifact_id="lesson-1",
            artifact_type="lesson",
            generation_id="run-1:artifact:2",
            version=2,
            title="Current lesson",
        ).as_state(),
    ]

    current = current_generation_artifact_references(references, "run-1:artifact:2")

    assert current == [references[1]]


def test_specialist_result_is_the_adr_053_name_for_artifact_persistence_result() -> None:
    """#464: SpecialistResult is an alias, not a parallel type -- both names
    must resolve to the same object and construct identically."""
    assert SpecialistResult is ArtifactPersistenceResult

    result = SpecialistResult(artifact=_artifact())
    assert isinstance(result, ArtifactPersistenceResult)
