from __future__ import annotations

import pytest

from packages.agents.teaching_pack.nodes import JsonObject, TeachingPackState, _compliance_gate
from packages.agents.teaching_pack.stages import StageEnum


ANSWER_KEY_MARKERS = (
    "Answer Key:",
    "answer key",
    "Correct Answer:",
    "[ANSWER]",
    "✓ Correct:",
    "Đáp án:",
    "Đáp án đúng:",
)


def _artifact() -> JsonObject:
    return {
        "artifact_id": "quiz-1",
        "artifact_type": "quiz",
        "theme": "default",
        "title": "Photosynthesis Check",
        "sections": [{"title": "Practice", "content": "Answer the questions."}],
        "metadata": {},
        "accessibility": {"language": "en"},
    }


def _snapshot(student_html: str, teacher_html: str = "Answer Key: 1=B 2=A") -> JsonObject:
    return {
        "snapshot_id": "snap-quiz-1",
        "student_rendered_html": student_html,
        "rendered_html": _html(teacher_html),
    }


def _html(body: str) -> str:
    return (
        "<!DOCTYPE html><html lang='en'><head>"
        "<meta name='viewport' content='width=device-width'></head>"
        f"<body>oh-my-class {body}</body></html>"
    )


def _state(snapshot: JsonObject) -> TeachingPackState:
    return TeachingPackState(
        run_id="run-answer-leak",
        current_stage=StageEnum.COMPLIANCE_GATE,
        artifacts=[_artifact()],
        rendered_snapshots=[snapshot],
    )


class TestStudentHtmlInvariant05:
    @pytest.mark.parametrize("marker", ANSWER_KEY_MARKERS)
    def test_student_html_answer_markers_fail_compliance_gate(self, marker: str) -> None:
        result = _compliance_gate(_state(_snapshot(_html(f"Question 1. {marker} B"))))
        compliance_result = result.get("compliance_result", {})
        assert isinstance(compliance_result, dict)
        violations = compliance_result.get("violations", [])
        assert isinstance(violations, list)

        assert result.get("compliance_passed") is False
        assert "answer_key_leakage" in violations

    def test_clean_student_html_passes_while_teacher_answer_key_is_allowed(self) -> None:
        result = _compliance_gate(_state(_snapshot(_html("Question 1. Choose the best answer."))))

        assert result.get("compliance_passed") is True

    def test_nested_question_card_answer_field_passes_content_gate(self) -> None:
        # A question_card's "answer" field is the sanctioned safe location for
        # correct answers (prompt_contract.py) — real leak protection for the
        # student view is the marker checks above, run against student_rendered_html.
        from packages.agents.gates.presentation.answer_key_guard import check_answer_key_leakage

        result = check_answer_key_leakage({
            "artifact_type": "quiz",
            "sections": [{"components": [{"type": "question_card", "text": "2+2?", "answer": "4"}]}],
        })

        assert result["passed"] is True
