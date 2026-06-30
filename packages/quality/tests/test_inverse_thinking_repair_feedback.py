from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import english_grammar_pack
from packages.quality.layer2_content.inverse_thinking import validate_inverse_thinking_pack


def test_repair_feedback_includes_case_field_severity_and_instruction() -> None:
    payload = english_grammar_pack()
    payload["cases"][0]["safe_zone"] = "Remember the tense name."

    result = validate_inverse_thinking_pack(payload)
    issue = result.issues[0]

    assert issue.case_id == "case-present-perfect"
    assert issue.field_path == "cases.case-present-perfect.safe_zone"
    assert issue.severity == "critical"
    assert "boundary" in issue.repair_instruction.lower()
