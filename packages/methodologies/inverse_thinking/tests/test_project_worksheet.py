from __future__ import annotations

from common.contracts.tests.inverse_thinking_fixtures import math_misconception_pack
from packages.methodologies.inverse_thinking import project_worksheet


def test_project_worksheet_includes_evidence_clue_safe_zone_and_summary_practice() -> None:
    projection = project_worksheet(math_misconception_pack())
    text = "\n".join(str(component) for component in projection.student_components)

    assert projection.artifact_type == "worksheet"
    assert "case-fraction-addition" in projection.case_ids
    assert "Evidence" in text
    assert "halves and thirds" in text
    assert "safe-zone" in text.lower()
    assert "summary" in text.lower()
