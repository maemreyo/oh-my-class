from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack


def test_answer_key_leakage_in_student_field_fails_critically() -> None:
    payload = english_grammar_pack()
    payload["cases"][0]["student_task"] = "Correct answer: I visited Da Nang yesterday."

    result = validate_inverse_thinking_pack(payload)

    assert not result.passed
    assert result.issues[0].severity == "critical"
    assert result.issues[0].code == "answer_key_leakage"
    assert result.issues[0].field_path == "cases.case-present-perfect.student_task"
