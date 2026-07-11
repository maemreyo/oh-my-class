from __future__ import annotations

import pytest

from common.contracts.artifact_projection_mapper import (
    ArtifactProjectionConversionError,
    artifact_content_from_document,
    artifact_document_from_content,
)


def _quiz() -> dict[str, object]:
    return {
        "artifact_type": "quiz",
        "title": "Fractions quiz",
        "theme": "default",
        "sections": [{
            "title": "Questions",
            "components": [{
                "type": "question_card",
                "id": "question-1",
                "text": "Which fraction is one half?",
                "options": {"A": "2/4", "B": "1/3"},
                "answer": "A",
                "explain": "Two fourths equals one half.",
            }],
        }],
        "metadata": {"answer_set": {"teacher_only": True}},
        "accessibility": {"language": "en"},
    }


def test_assessment_projection_round_trip_excludes_answer_material() -> None:
    document = artifact_document_from_content(
        _quiz(),
        document_id="document-quiz-1",
        artifact_id="quiz-1",
    )

    projection = artifact_content_from_document(document, theme="default")

    assert document.payload.questions[0].options[0].entity_id == "A"
    assert "answer_set" not in document.model_dump(mode="json")
    assert "answer" not in projection.sections[0]["components"][0]
    assert "explain" not in projection.sections[0]["components"][0]
    assert projection.sections[0]["components"][0]["options"] == {"A": "2/4", "B": "1/3"}


def test_mapper_rejects_assessment_without_question_cards() -> None:
    invalid = _quiz()
    invalid["sections"] = [{"title": "Questions", "components": []}]

    with pytest.raises(ArtifactProjectionConversionError, match="question_card"):
        artifact_document_from_content(
            invalid,
            document_id="document-quiz-1",
            artifact_id="quiz-1",
        )


def test_rich_lesson_projection_preserves_components_without_teacher_answers() -> None:
    lesson = {
        "artifact_type": "lesson",
        "title": "Fractions lesson",
        "theme": "ocean",
        "sections": [{
            "id": "section-1",
            "title": "Explore fractions",
            "components": [
                {"type": "callout", "variant": "note", "title": "Remember", "body": "Equal parts have equal size."},
                {
                    "type": "question_card",
                    "id": "question-1",
                    "text": "Which fraction is one half?",
                    "options": {"A": "2/4", "B": "1/3"},
                    "answer": "A",
                    "explain": "Two fourths equals one half.",
                },
            ],
        }],
        "metadata": {},
        "accessibility": {"language": "en"},
    }

    document = artifact_document_from_content(
        lesson,
        document_id="document-lesson-1",
        artifact_id="lesson-1",
    )
    projection = artifact_content_from_document(document)

    assert document.payload.payload_kind == "rich_document"
    component = projection.sections[0]["components"][1]
    assert component["type"] == "question_card"
    assert "answer" not in component
    assert "explain" not in component


def test_answer_key_projection_remains_teacher_audience() -> None:
    answer_key = {
        "artifact_type": "answer_key",
        "title": "Answer Key: Fractions",
        "theme": "default",
        "sections": [{"title": "Question 1", "components": [{"type": "paragraph", "text": "Answer: A"}]}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }

    document = artifact_document_from_content(
        answer_key,
        document_id="document-answer-key-1",
        artifact_id="answer-key-1",
    )

    assert document.audience == "teacher"


def test_slide_deck_projection_uses_typed_slide_deck_payload() -> None:
    deck = {
        "deck_id": "deck-fractions",
        "title": "Equivalent Fractions",
        "locale": "en-US",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [{
            "slide_id": "slide-1",
            "title": "Equivalent Fractions",
            "layout": "title",
            "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
            "blocks": [{
                "block_id": "block-1",
                "block_type": "heading",
                "body": "Equivalent fractions name the same value.",
            }],
        }],
        "accessibility": {
            "reading_level": "Grade 5",
            "language": "en",
            "alt_text_required": True,
            "keyboard_navigation": True,
        },
        "media_policy": {
            "default_tier": "packaged",
            "online_optional_allowed": False,
            "fallback_required": True,
        },
    }
    content = {
        "artifact_type": "slide_deck",
        "title": "Equivalent Fractions",
        "theme": "default",
        "sections": [{"title": "Deck", "components": [{"type": "paragraph", "text": "Deck ready."}]}],
        "metadata": {"slide_deck_data": deck},
        "accessibility": {"language": "en"},
    }

    document = artifact_document_from_content(
        content,
        document_id="document-slide-deck-1",
        artifact_id="slide-deck-1",
    )
    projection = artifact_content_from_document(document)

    assert document.payload.payload_kind == "slide_deck_document"
    assert document.payload.slide_deck is not None
    assert document.payload.slide_deck.deck_id == "deck-fractions"
    assert projection.metadata["slide_deck_data"]["deck_id"] == "deck-fractions"
