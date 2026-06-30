from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import science_misconception_pack
from packages.methodologies.inverse_thinking import project_drill, project_lesson, project_quiz


def test_quiz_and_drill_reuse_canonical_case_without_contradicting_lesson() -> None:
    payload = science_misconception_pack()
    lesson = project_lesson(payload)
    quiz = project_quiz(payload)
    drill = project_drill(payload)

    assert quiz.artifact_type == "quiz"
    assert drill.artifact_type == "drill"
    assert quiz.case_ids == lesson.case_ids == drill.case_ids
    assert "case-current-consumption" in str(quiz.student_components)
    assert "case-current-consumption" in str(drill.student_components)
    assert "same at every point" in str(quiz.student_components)
    assert "same at every point" in str(drill.student_components)
