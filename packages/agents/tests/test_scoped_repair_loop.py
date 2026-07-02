from __future__ import annotations

from packages.agents.teaching_pack.scoped_repair import (
    ContentVersionStore,
    JsonObject,
    scoped_repair_plan,
    scoped_repair_update,
)
from packages.agents.teaching_pack.scoped_regeneration import apply_scoped_section_edit


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
