from __future__ import annotations

from packages.agents.teaching_pack.scoped_repair import (
    ContentVersionStore,
    JsonObject,
    scoped_repair_plan,
    scoped_repair_update,
)
from packages.agents.teaching_pack.scoped_regeneration import (
    apply_scoped_section_edit,
    apply_scoped_slide_deck_block_edit_on_artifacts,
)
from packages.agents.teaching_pack.scoped_repair_models import RepairRequest, ScopedRepairPlan


def test_repair_request_is_the_adr_053_name_for_scoped_repair_plan() -> None:
    """#464: RepairRequest is an alias, not a parallel type."""
    assert RepairRequest is ScopedRepairPlan


def test_scoped_repair_replaces_only_target_section_and_versions_lineage() -> None:
    artifact = _artifact()
    store = ContentVersionStore()
    first = store.snapshot(artifact, reason="initial")
    plan = scoped_repair_plan(
        "lesson-1.sections[1].components[0]: pedagogical_mismatch: missing objective",
    )

    update = scoped_repair_update(artifact, plan, store, critique="missing objective", max_attempts=2)

    assert update.artifact["sections"][0] == artifact["sections"][0]
    assert update.artifact["sections"][1] != artifact["sections"][1]
    assert update.version.parent_hash == first.content_hash
    assert update.diff["changed_path"] == "lesson-1.sections[1]"
    assert update.event["event_name"] == "teaching_pack.content_version.created"


def test_failure_class_routes_to_scoped_strategy() -> None:
    assert scoped_repair_plan("a.sections[0]: schema_invalid: x").strategy == "schema_repair"
    assert scoped_repair_plan("a.sections[0]: factual_uncertainty: x").strategy == "research_enrichment"
    assert scoped_repair_plan("a.sections[0]: pedagogical_mismatch: x").strategy == "replan_blueprint"
    assert scoped_repair_plan("a.sections[0]: external_asset: x").strategy == "presentation_repair"
    assert scoped_repair_plan("a.sections[0]: methodology component missing: x").strategy == "inject_required_component"


def test_bounded_local_rereview_escalates_residual_issue() -> None:
    artifact = _artifact()
    store = ContentVersionStore()
    plan = scoped_repair_plan("lesson-1.sections[1]: pedagogical_mismatch: missing objective")

    update = scoped_repair_update(
        artifact,
        plan,
        store,
        critique="missing objective",
        max_attempts=1,
        force_residual_failure=True,
    )

    assert update.escalate_to_teacher is True
    assert update.event["payload"]["authority"] == "teacher_suggested"


def test_low_risk_auto_applies_but_approved_content_does_not_silently_change() -> None:
    artifact = {**_artifact(), "approved": True}
    store = ContentVersionStore()
    plan = scoped_repair_plan("lesson-1.sections[0]: schema_invalid: bad shape")

    update = scoped_repair_update(artifact, plan, store, critique="bad shape", max_attempts=2)

    assert update.artifact == artifact
    assert update.event["payload"]["authority"] == "teacher_suggested"
    assert update.diff["status"] == "blocked_approved_content"


def test_teacher_section_edit_updates_only_target_section_with_event() -> None:
    artifact = _artifact()

    update = apply_scoped_section_edit([artifact], {
        "edit_type": "scoped_section",
        "section_edit": {
            "artifact_id": "lesson-1",
            "section_id": "practice",
            "replacement_content": "Teacher revised practice.",
            "rationale": "Better scaffolded practice.",
        },
    })

    artifacts = update["artifacts"]
    assert isinstance(artifacts, list)
    edited = artifacts[0]
    assert isinstance(edited, dict)
    sections = edited["sections"]
    assert isinstance(sections, list)
    assert sections[0] == artifact["sections"][0]
    assert isinstance(sections[1], dict)
    assert sections[1]["content"] == "Teacher revised practice."
    event = update["content_update_event"]
    assert isinstance(event, dict)
    assert event["event_name"] == "teaching_pack.content_version.created"


def test_slide_deck_block_edit_updates_only_target_block_with_event() -> None:
    """SDE-04: `apply_scoped_section_edit` above no-ops on slide_deck artifacts
    (its `sections` list check fails closed -- they're `slides[].blocks[]`,
    not flat sections), so this is the gate-resume wiring's slide-deck-scoped
    equivalent, mirroring the test above one-for-one."""
    artifact = _slide_deck_artifact()

    update = apply_scoped_slide_deck_block_edit_on_artifacts([artifact], {
        "edit_type": "scoped_slide_deck_block",
        "slide_deck_block_edit": {
            "artifact_id": "deck-artifact-1",
            "block_id": "block-1",
            "new_content": "Teacher-revised heading.",
            "rationale": "Clarify the hook.",
        },
    })

    artifacts = update["artifacts"]
    assert isinstance(artifacts, list)
    edited = artifacts[0]
    assert isinstance(edited, dict)
    updated_deck = edited["metadata"]["slide_deck_data"]
    assert updated_deck["slides"][0]["blocks"][0]["body"] == "Teacher-revised heading."
    # Both embedding spots (metadata.slide_deck_data and sections[0].slide_deck)
    # must stay in sync, or a downstream reader of either sees stale content.
    assert edited["sections"][0]["slide_deck"]["slides"][0]["blocks"][0]["body"] == "Teacher-revised heading."
    event = update["content_update_event"]
    assert isinstance(event, dict)
    assert event["event_name"] == "teaching_pack.content_version.created"
    assert event["payload"]["authority"] == "teacher_edit"


def test_slide_deck_block_edit_no_ops_when_edit_type_mismatched() -> None:
    artifact = _slide_deck_artifact()

    update = apply_scoped_slide_deck_block_edit_on_artifacts([artifact], {"edit_type": "scoped_section"})

    assert update["artifacts"][0] == artifact
    assert "content_update_event" not in update


def test_slide_deck_block_edit_no_ops_for_unknown_block_id() -> None:
    """An invalid edit (bad block_id, or a body failing SDE-02's registry
    bounds) is rejected -- the gate-resume flow degrades gracefully, same
    convention as `apply_scoped_section_edit`'s no-op-on-invalid-input."""
    artifact = _slide_deck_artifact()

    update = apply_scoped_slide_deck_block_edit_on_artifacts([artifact], {
        "edit_type": "scoped_slide_deck_block",
        "slide_deck_block_edit": {
            "artifact_id": "deck-artifact-1",
            "block_id": "block-does-not-exist",
            "new_content": "New body.",
        },
    })

    assert update["artifacts"][0] == artifact
    assert "content_update_event" not in update


def _slide_deck_artifact() -> JsonObject:
    deck: JsonObject = {
        "deck_id": "deck-1",
        "title": "Fractions Deck",
        "locale": "en-US",
        "theme": "default",
        "surfaces": {
            "student": {"mode": "presentation", "export_format": "html"},
            "teacher": {"mode": "teacher_guide", "export_format": "html"},
            "print": {"mode": "print", "export_format": "html"},
        },
        "slides": [
            {
                "slide_id": "slide-1",
                "title": "Intro",
                "layout": "title",
                "progression": {"step_index": 1, "reveal_policy": "all_at_once"},
                "blocks": [
                    {"block_id": "block-1", "block_type": "heading", "body": "Original heading."},
                ],
            },
        ],
        "accessibility": {"reading_level": "grade_5", "language": "en"},
        "media_policy": {"default_tier": "packaged", "online_optional_allowed": False, "fallback_required": True},
    }
    return {
        "artifact_id": "deck-artifact-1",
        "artifact_type": "slide_deck",
        "title": "Fractions Deck",
        "sections": [{"title": "Fractions Deck", "slide_deck": deck}],
        "metadata": {"slide_deck_data": deck},
        "accessibility": {"language": "en"},
    }


def _artifact() -> JsonObject:
    return {
        "artifact_id": "lesson-1",
        "artifact_type": "lesson",
        "title": "Fractions Lesson",
        "sections": [
            {"section_id": "intro", "content": "Keep this section."},
            {"section_id": "practice", "content": "Repair this section."},
        ],
        "metadata": {},
        "accessibility": {"language": "en"},
    }
