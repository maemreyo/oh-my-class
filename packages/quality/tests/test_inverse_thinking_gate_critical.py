from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import (
    english_grammar_pack,
    math_misconception_pack,
    science_misconception_pack,
)
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("disaster", "Use simple past with yesterday."),
        ("key_clues", []),
        ("safe_zone", "Remember the tense name."),
        ("filing_note", "Rule."),
    ],
)
def test_critical_failures_name_case_field_and_repair(field: str, value) -> None:
    payload = english_grammar_pack()
    payload["cases"][0][field] = value

    result = validate_inverse_thinking_pack(payload)

    assert not result.passed
    assert result.issues[0].severity == "critical"
    assert result.issues[0].case_id == "case-present-perfect"
    assert result.issues[0].field_path == f"cases.case-present-perfect.{field}"
    assert result.issues[0].repair_instruction


@pytest.mark.parametrize("payload", [english_grammar_pack(), math_misconception_pack(), science_misconception_pack()])
def test_subject_agnostic_fixtures_pass_without_issues(payload: dict) -> None:
    result = validate_inverse_thinking_pack(payload)

    assert result.passed
    assert result.issues == []
