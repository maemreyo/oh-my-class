from __future__ import annotations

import pytest

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("disaster", "This is wrong.", "generic_disaster"),
        ("title", "Exercise", "missing_signature_element"),
        ("student_task", "Hiện trường → Manh mối → Vùng an toàn → Biên bản", "over_copied_template"),
    ],
)
def test_major_warnings_include_repair_guidance(field: str, value: str, code: str) -> None:
    payload = english_grammar_pack()
    payload["cases"][0][field] = value

    result = validate_inverse_thinking_pack(payload)

    assert not result.passed
    assert result.issues[0].severity == "major"
    assert result.issues[0].code == code
    assert result.issues[0].repair_instruction


def test_weak_metaphor_consistency_warns_when_frame_and_case_language_conflict() -> None:
    payload = english_grammar_pack()
    payload["creative_frame"] = "courtroom_trial"

    result = validate_inverse_thinking_pack(payload)

    assert not result.passed
    assert result.issues[0].severity == "major"
    assert result.issues[0].code == "weak_metaphor_consistency"
