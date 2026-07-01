from __future__ import annotations

from common.contracts.methodology_registry import (
    METHODOLOGY_REGISTRY,
    METHODOLOGY_TAG_VALUES,
    build_composite_projection_plan,
    compatibility_for,
    pair_rule_for,
)


def test_registry_entries_define_teacher_metadata_and_supported_surfaces() -> None:
    assert tuple(entry.tag for entry in METHODOLOGY_REGISTRY) == METHODOLOGY_TAG_VALUES
    for entry in METHODOLOGY_REGISTRY:
        assert entry.tag
        assert entry.label_en
        assert entry.label_vi
        assert entry.description
        assert entry.required_components
        assert entry.supported_artifacts
        assert entry.export_formats


def test_every_tag_pair_has_defined_compatibility() -> None:
    statuses = {"compatible", "conflict", "neutral"}
    for left in METHODOLOGY_TAG_VALUES:
        for right in METHODOLOGY_TAG_VALUES:
            assert compatibility_for(left, right) in statuses
            assert pair_rule_for(left, right).status in statuses
            assert pair_rule_for(left, right).rationale


def test_self_pairs_are_compatible() -> None:
    for tag in METHODOLOGY_TAG_VALUES:
        assert compatibility_for(tag, tag) == "compatible"


def test_known_conflict_and_compatible_pairs_are_classified() -> None:
    assert compatibility_for("shy_student_1on1", "timed_quiz") == "conflict"
    assert compatibility_for("inverse_thinking", "active_recall") == "compatible"


def test_semantic_anchoring_methodology_metadata_is_registered() -> None:
    entries = {entry.tag: entry for entry in METHODOLOGY_REGISTRY}
    entry = entries["semantic_anchoring"]

    assert entry.label_vi == "Neo Tư Duy / Neo Mindset"
    assert entry.required_components == ("semantic_anchor_cluster", "practice_set")
    assert entry.supported_artifacts == ("lesson", "worksheet", "recap")
    assert entry.export_formats == ("html", "gift", "h5p")


def test_composite_projection_plan_preserves_registry_order_and_sources() -> None:
    plan = build_composite_projection_plan(["active_recall", "inverse_thinking"])

    assert plan.ordered_tags == ("active_recall", "inverse_thinking")
    assert "active_recall_prompt" in plan.required_components
    assert "case_flow" in plan.required_components
    assert plan.source_methodology_tags["active_recall_prompt"] == ("active_recall",)
    assert plan.source_methodology_tags["case_flow"] == ("inverse_thinking",)
