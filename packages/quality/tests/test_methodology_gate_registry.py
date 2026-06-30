from __future__ import annotations

from common.contracts.methodology_registry import METHODOLOGY_REGISTRY
from common.contracts.methodology_registry import build_composite_projection_plan
from packages.quality.layer2_content.methodology import check_methodology_compliance, validate_composite_projection_plan


def test_gate_reports_registry_defined_requirements_when_missing() -> None:
    gated_entries = [
        entry
        for entry in METHODOLOGY_REGISTRY
        if entry.tag not in {"timed_quiz", "why_wrong_reasoning"}
    ]

    for entry in gated_entries:
        result = check_methodology_compliance([], [entry.tag])

        assert result.passed is False
        assert result.violations[0].tag == entry.tag
        assert entry.label_en in result.violations[0].message
        for component in entry.required_components:
            assert component in result.violations[0].message


def test_composite_projection_gate_names_source_tag_for_missing_component() -> None:
    plan = build_composite_projection_plan(["inverse_thinking", "active_recall"])

    result = validate_composite_projection_plan(plan, [{"components": [{"type": "case_flow"}, {"type": "table"}]}])

    assert result.passed is False
    assert result.violations[0].tag == "active_recall"
    assert "active_recall_prompt" in result.violations[0].message


def test_composite_projection_gate_passes_when_all_sources_present() -> None:
    plan = build_composite_projection_plan(["inverse_thinking", "active_recall"])

    result = validate_composite_projection_plan(
        plan,
        [{"components": [{"type": "case_flow"}, {"type": "table"}, {"type": "active_recall_prompt"}]}],
    )

    assert result.passed is True
