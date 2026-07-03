"""Full pipeline integration tests: multi-artifact state through step_12_finalize."""

from __future__ import annotations

from typing import Any

import pytest

from packages.agents.nodes.finalize import step_12_finalize
from packages.agents.nodes.state import NodeState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def lesson_artifact() -> dict[str, Any]:
    return {
        "artifact_id": "lesson-pipeline-001",
        "artifact_type": "lesson",
        "title": "Travel Vocabulary: Airport Verbs",
        "theme": "default",
        "sections": [
            {
                "title": "Key Vocabulary",
                "content": "Learn these airport action verbs.",
                "components": [
                    {
                        "type": "vocab_cluster",
                        "title": "Airport Verbs",
                        "description": "Actions at the airport",
                        "items": [
                            {
                                "word": "check in",
                                "definition": "register for a flight",
                                "example": "We check in two hours before departure.",
                            },
                        ],
                    },
                ],
            },
            {
                "title": "Practice",
                "content": "Test your understanding.",
                "components": [
                    {
                        "type": "question_card",
                        "id": 1,
                        "text": "What does 'check in' mean at an airport?",
                        "options": {
                            "A": "Criticize someone",
                            "B": "Register for a flight",
                            "C": "Leave the airport",
                            "D": "Buy snacks",
                        },
                        "answer": "B",
                        "explain": "SENTINEL_LESSON_EXPLAIN",
                        "wrong_reasons": {"A": "SENTINEL_LESSON_WRONG_A"},
                    },
                ],
            },
            {
                "title": "Teacher Notes",
                "content": "SENTINEL_LESSON_TEACHER_SECTION",
                "teacher_only": True,
            },
        ],
        "metadata": {"subject": "English", "grade_level": "Grade 8"},
        "accessibility": {"language": "en"},
    }


@pytest.fixture(scope="module")
def quiz_artifact() -> dict[str, Any]:
    return {
        "artifact_id": "quiz-pipeline-001",
        "artifact_type": "quiz",
        "title": "Airport Vocabulary Quiz",
        "theme": "default",
        "sections": [
            {
                "id": "q1",
                "content": "Which verb means to get onto a plane?",
                "options": {
                    "A": "check in",
                    "B": "board",
                    "C": "depart",
                    "D": "transit",
                },
                "correct_answer": "B",
                "explanation": "SENTINEL_QUIZ_EXPLAIN",
            },
        ],
        "metadata": {"subject": "English", "grade_level": "Grade 8"},
        "accessibility": {"language": "en"},
    }


def _make_state(
    artifacts: list[dict[str, Any]],
    export_formats: list[str] | None = None,
) -> NodeState:
    return NodeState(
        raw_request="Teach travel vocabulary",
        teacher_id="t-pipeline-001",
        class_info={"grade": 8, "subject": "English"},
        run_id="pipeline-integration-test",
        artifact_types=["lesson"],
        theme="default",
        artifacts=artifacts,
        export_formats=export_formats or ["html"],
        exported_files=[],
        current_step=11,
        research_policy="basic",
    )


# ---------------------------------------------------------------------------
# Module-scoped combined result to avoid rebuilding the renderer per-test
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def multi_artifact_result(
    lesson_artifact: dict[str, Any],
    quiz_artifact: dict[str, Any],
) -> dict[str, Any]:
    """Render lesson + quiz in one step_12_finalize call (builds renderer once)."""
    state = _make_state([lesson_artifact, quiz_artifact])
    return step_12_finalize(state)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_lesson_renders_to_valid_standalone_html(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        lesson_file = next(f for f in files if f["artifact_id"] == "lesson-pipeline-001")
        html = lesson_file["content"]

        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "<head" in html
        assert "<body" in html
        assert "oh-my-class" in html

    def test_lesson_contains_student_content(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        lesson_file = next(f for f in files if f["artifact_id"] == "lesson-pipeline-001")
        html = lesson_file["content"]

        assert "Airport Verbs" in html
        assert "check in" in html
        assert "register for a flight" in html

    def test_lesson_strips_teacher_only_content(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        lesson_file = next(f for f in files if f["artifact_id"] == "lesson-pipeline-001")
        html = lesson_file["content"]

        assert "SENTINEL_LESSON_EXPLAIN" not in html
        assert "SENTINEL_LESSON_WRONG_A" not in html
        assert "SENTINEL_LESSON_TEACHER_SECTION" not in html

    def test_quiz_hides_teacher_explanation(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        quiz_file = next(f for f in files if f["artifact_id"] == "quiz-pipeline-001")
        html = quiz_file["content"]

        assert "SENTINEL_QUIZ_EXPLAIN" not in html

    def test_quiz_shows_question_text(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        quiz_file = next(f for f in files if f["artifact_id"] == "quiz-pipeline-001")
        html = quiz_file["content"]

        assert "Which verb means to get onto a plane?" in html

    def test_multiple_artifacts_produce_multiple_files(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        assert len(files) == 2

        artifact_ids = {f["artifact_id"] for f in files}
        assert artifact_ids == {"lesson-pipeline-001", "quiz-pipeline-001"}

    def test_exported_file_metadata_fields(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        files = multi_artifact_result["exported_files"]
        lesson_file = next(f for f in files if f["artifact_id"] == "lesson-pipeline-001")

        assert lesson_file["format"] == "html"
        assert lesson_file["title"] == "Travel Vocabulary: Airport Verbs"
        assert lesson_file["artifact_type"] == "lesson"
        assert lesson_file["theme"] == "default"

    def test_no_external_urls_in_any_rendered_file(
        self,
        multi_artifact_result: dict[str, Any],
    ) -> None:
        for f in multi_artifact_result["exported_files"]:
            assert "http://" not in f["content"], f"{f['artifact_id']} contains http://"
            assert "https://" not in f["content"], f"{f['artifact_id']} contains https://"

    def test_teacher_only_artifact_excluded(
        self,
        lesson_artifact: dict[str, Any],
    ) -> None:
        teacher_artifact: dict[str, Any] = {
            **lesson_artifact,
            "artifact_id": "teacher-only-001",
            "title": "Teacher Guide",
            "teacher_only": True,
        }
        state = _make_state([lesson_artifact, teacher_artifact])
        result = step_12_finalize(state)

        exported_ids = {f["artifact_id"] for f in result["exported_files"]}
        assert "teacher-only-001" not in exported_ids
        assert "lesson-pipeline-001" in exported_ids

    def test_artifact_with_external_url_triggers_export_error(
        self,
        lesson_artifact: dict[str, Any],
    ) -> None:
        bad_artifact: dict[str, Any] = {
            "artifact_id": "bad-url-001",
            "artifact_type": "lesson",
            "title": "Bad Lesson",
            "theme": "default",
            "sections": [
                {
                    "title": "External reference",
                    "content": "See https://external-resource.example.com for details.",
                },
            ],
        }
        state = _make_state([lesson_artifact, bad_artifact])
        result = step_12_finalize(state)

        assert result.get("export_ready") is False
        assert result.get("fail_layer") == "export"

        exported_ids = {f["artifact_id"] for f in result["exported_files"]}
        assert "bad-url-001" not in exported_ids
        assert "lesson-pipeline-001" in exported_ids
