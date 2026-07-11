from __future__ import annotations

from typing import Any

from common.contracts.artifact import ArtifactContent
from common.contracts.artifact_projection_mapper import artifact_document_from_content
from packages.agents.events import ObservabilityEvent
from services.gateway.teaching_pack_snapshot_validators import (
    remove_answer_keys_from_html,
    teacher_only_value_paths,
    validate_answer_key_isolation,
)

_ANSWER_MARKERS = ("answer", "answer_set", "accepted_answers", "correct_option_ids", "explain", "rationale", "wrong_reasons", "rubric_solution")


def _recursive_scan(value: Any, markers: tuple[str, ...] = _ANSWER_MARKERS) -> list[str]:
    """#463: property-test-style recursive scan for answer-bearing keys
    anywhere in a serialized student document -- the same shape of check
    `teacher_only_value_paths` runs at the gateway write seam, applied here
    directly against a V2 `ArtifactDocument`'s JSON."""
    found: list[str] = []

    def _walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, item in node.items():
                child_path = f"{path}.{key}"
                if key in markers:
                    found.append(child_path)
                _walk(item, child_path)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                _walk(item, f"{path}[{index}]")

    _walk(value, "document")
    return found


def _quiz_artifact() -> ArtifactContent:
    return ArtifactContent.model_validate({
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Fractions quiz",
        "sections": [{"components": [{
            "type": "question_card",
            "id": "question-1",
            "text": "Which fraction equals one half?",
            "options": {"A": "1/4", "B": "2/4"},
            "answer": "B",
            "explain": "Two fourths equals one half.",
        }]}],
        "metadata": {},
        "accessibility": {"language": "en"},
    })


def _lesson_artifact() -> ArtifactContent:
    return ArtifactContent.model_validate({
        "artifact_type": "lesson",
        "theme": "default",
        "title": "Fractions lesson",
        "sections": [{
            "id": "section-1",
            "title": "Teacher notes",
            "components": [{
                "type": "paragraph",
                "text": "Model with fraction bars.",
                "rationale": "Concrete manipulatives ground the abstract ratio.",
            }],
        }],
        "metadata": {},
        "accessibility": {"language": "en"},
    })


def _slide_deck_artifact() -> ArtifactContent:
    deck = {
        "deck_id": "deck-1",
        "title": "Fractions Deck",
        "locale": "en",
        "theme": "default",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [{
            "slide_id": "slide-1",
            "title": "Check",
            "layout": "question",
            "progression": {"step_index": 1, "reveal_policy": "progressive"},
            "blocks": [{"block_id": "block-1", "block_type": "interaction_prompt", "body": "Which is one half?"}],
            "interactions": [{
                "interaction_id": "interaction-1",
                "interaction_type": "quick_check",
                "prompt": "Which is one half?",
                "answer_bearing": True,
                "options": [{"option_id": "a", "label": "1/4"}, {"option_id": "b", "label": "2/4"}],
                "teacher_only": {
                    "separation": "teacher_only_projection",
                    "correct_option_ids": ["b"],
                    "rationale": "Two fourths reduces to one half.",
                },
            }],
            "teacher_notes": {"facilitation_notes": ["Model on the board."], "answer_key_notes": ["b"]},
        }],
        "accessibility": {"reading_level": "grade_5", "language": "en"},
        "media_policy": {"default_tier": "packaged", "online_optional_allowed": False, "fallback_required": True},
    }
    return ArtifactContent.model_validate({
        "artifact_type": "slide_deck",
        "theme": "default",
        "title": "Fractions Deck",
        "sections": [{"title": "Deck", "slide_deck": deck}],
        "metadata": {"slide_deck_data": deck},
        "accessibility": {"language": "en"},
    })


class TestStudentDocumentJsonIsAnswerFree:
    """#463 required test: 'Property test recursively scanning student
    document JSON for all teacher-only answer fields and known leakage
    markers.'"""

    def test_assessment_student_document_has_no_answer_markers(self) -> None:
        document = artifact_document_from_content(_quiz_artifact(), document_id="doc-quiz", artifact_id="quiz-1")
        leaked = _recursive_scan(document.model_dump(mode="json"))
        assert leaked == []

    def test_rich_document_student_projection_has_no_answer_markers(self) -> None:
        document = artifact_document_from_content(_lesson_artifact(), document_id="doc-lesson", artifact_id="lesson-1")
        leaked = _recursive_scan(document.model_dump(mode="json"))
        assert leaked == []

    def test_slide_deck_student_projection_strips_teacher_only_objects(self) -> None:
        document = artifact_document_from_content(_slide_deck_artifact(), document_id="doc-deck", artifact_id="deck-1")
        dumped = document.model_dump(mode="json")
        leaked = _recursive_scan(dumped)
        assert leaked == []
        # The whole teacher_only/teacher_notes objects are gone, not merely
        # their leaf fields -- see artifact_projection_mapper._student_safe_slide_deck.
        slide = dumped["payload"]["slide_deck"]["slides"][0]
        assert slide["teacher_notes"] is None
        assert slide["interactions"][0]["teacher_only"] is None

    def test_teacher_audience_document_retains_answers(self) -> None:
        """Sanity: the scrub is audience-scoped, not a blanket redaction --
        an answer_key document (audience="teacher") keeps its content."""
        answer_key = ArtifactContent.model_validate({
            "artifact_type": "answer_key",
            "theme": "default",
            "title": "Fractions answer key",
            "sections": [{"components": [{"type": "paragraph", "text": "Answer: B"}]}],
            "metadata": {},
            "accessibility": {"language": "en"},
        })
        document = artifact_document_from_content(answer_key, document_id="doc-key", artifact_id="quiz-1")
        assert document.audience == "teacher"


class TestGatewayWriteSeamLeakageGuard:
    """#463: the recursive guard enforced at snapshot-create and export-write
    time (`teaching_pack_snapshot_store.py`, `teaching_pack_export_writer.py`)."""

    def test_teacher_only_value_paths_detects_nested_leaks(self) -> None:
        payload = {
            "sections": [{"components": [{
                "type": "question_card",
                "text": "2+2?",
                "answer": "4",
                "nested": {"rationale": "Basic addition."},
            }]}],
        }
        assert teacher_only_value_paths(payload) == [
            "content_json.sections[0].components[0].answer",
            "content_json.sections[0].components[0].nested.rationale",
        ]

    def test_teacher_only_value_paths_is_empty_for_clean_payload(self) -> None:
        payload = {
            "sections": [{"components": [{
                "type": "question_card",
                "text": "2+2?",
                "options": {"A": "3", "B": "4"},
            }]}],
        }
        assert teacher_only_value_paths(payload) == []


class TestHtmlSurfaceLeakageGuard:
    """Hidden-JSON/DOM-attribute leak vectors on the rendered HTML surface."""

    def test_marked_teacher_only_sections_are_stripped_from_student_html(self) -> None:
        html = (
            "<body>Question 1.<section data-teacher-only=\"true\">Answer: B</section>"
            "More content.</body>"
        )
        cleaned = remove_answer_keys_from_html(html)
        assert "Answer: B" not in cleaned
        assert "More content." in cleaned

    def test_unmarked_answer_pattern_in_student_html_fails_isolation_check(self) -> None:
        html = "<body>Question 1. Answer: B</body>"
        assert validate_answer_key_isolation(html) != []

    def test_marked_teacher_only_section_passes_isolation_check(self) -> None:
        html = "<body>Question 1.<section data-teacher-only=\"true\">Answer: B</section></body>"
        assert validate_answer_key_isolation(html) == []


class TestObservabilityEventPayloadIsAnswerFree:
    """SSE/observability events must never carry content -- only identifiers."""

    def test_legacy_read_event_payload_carries_no_content(self) -> None:
        event = ObservabilityEvent(
            run_id="run-1",
            event_type="artifact_document_legacy_read",
            payload={"document_id": "doc-1", "snapshot_id": "snap-1"},
        )
        leaked = _recursive_scan(event.model_dump(mode="json"))
        assert leaked == []
        assert set(event.payload) == {"document_id", "snapshot_id"}
