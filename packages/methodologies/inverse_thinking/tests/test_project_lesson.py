from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.methodologies.inverse_thinking import project_lesson


def test_project_lesson_preserves_case_flow_in_order() -> None:
    projection = project_lesson(english_grammar_pack())
    components = projection.student_components
    text = "\n".join(str(component) for component in components)

    assert projection.artifact_type == "lesson"
    assert "I have visited Da Nang yesterday" in text
    assert "yesterday marks a finished time" in text
    assert "I visited Da Nang yesterday" in text
    assert "Finished time markers" in text
    assert projection.summary_rows[0].case_id == "case-present-perfect"
