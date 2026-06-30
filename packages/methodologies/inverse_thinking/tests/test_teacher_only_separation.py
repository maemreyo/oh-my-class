from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.methodologies.inverse_thinking import (
    project_drill,
    project_lesson,
    project_quiz,
    project_worksheet,
)


@pytest.mark.parametrize("project", [project_lesson, project_worksheet, project_quiz, project_drill])
def test_student_projection_excludes_teacher_rationale_and_answer_key(project) -> None:
    projection = project(english_grammar_pack())
    student_text = str(projection.student_components)

    assert "The adverb yesterday conflicts" not in student_text
    assert "She met him last week" not in student_text
    assert projection.teacher_only.answer_key == "She met him last week."
