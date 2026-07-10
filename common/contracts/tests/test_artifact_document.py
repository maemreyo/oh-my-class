from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.answer_set import AnswerEntry, AnswerSet
from common.contracts.artifact_document import (
    ArtifactDocument,
    BlockDocument,
    DocumentSection,
    HeadingBlock,
)


def _block_document() -> BlockDocument:
    return BlockDocument(
        payload_kind="block_document",
        sections=[
            DocumentSection(
                entity_id="section-intro",
                title="Introduction",
                blocks=[
                    HeadingBlock(
                        entity_id="block-heading",
                        block_kind="heading",
                        level=2,
                        text="Plants need light",
                    ),
                ],
            ),
        ],
    )


def _document(**overrides: object) -> ArtifactDocument:
    values: dict[str, object] = {
        "document_id": "document-lesson-1",
        "artifact_id": "artifact-lesson-1",
        "artifact_type": "lesson",
        "version": 1,
        "language": "en",
        "audience": "student",
        "authority": "generated",
        "payload": _block_document(),
    }
    values.update(overrides)
    return ArtifactDocument(**values)


class TestArtifactDocument:
    def test_accepts_typed_block_payload_with_stable_entity_ids(self) -> None:
        document = _document()

        assert document.payload.payload_kind == "block_document"
        assert document.payload.sections[0].entity_id == "section-intro"

    def test_rejects_unknown_payload_discriminator(self) -> None:
        with pytest.raises(ValidationError, match="payload_kind"):
            _document(payload={"payload_kind": "unknown_document"})

    def test_rejects_assessment_payload_for_lesson(self) -> None:
        with pytest.raises(ValidationError, match="requires a block_document payload"):
            _document(
                payload={
                    "payload_kind": "assessment_document",
                    "questions": [
                        {"entity_id": "question-1", "prompt": "What is light?"},
                    ],
                },
            )


class TestAnswerSet:
    def test_keeps_answers_outside_student_artifact_document(self) -> None:
        answer_set = AnswerSet(
            answer_set_id="answers-quiz-1",
            source_document_id="document-quiz-1",
            source_version=1,
            entries=[
                AnswerEntry(
                    entity_id="answer-question-1",
                    question_id="question-1",
                    correct_option_ids=["option-b"],
                    rationale="Chlorophyll absorbs light.",
                ),
            ],
        )

        document = _document()

        assert answer_set.entries[0].question_id == "question-1"
        assert "answer_set" not in document.model_dump()
