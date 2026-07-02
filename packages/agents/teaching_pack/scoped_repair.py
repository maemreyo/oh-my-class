from __future__ import annotations

from typing import assert_never

from common.contracts.quality import QualityFailureClass, HealingStrategy
from packages.agents.teaching_pack.scoped_repair_models import (
    ContentVersion,
    ContentVersionStore,
    JsonObject,
    JsonValue,
    RepairDiff,
    RepairEvent,
    RepairScope,
    RepairStrategy,
    ScopedRepairPlan,
    ScopedRepairUpdate,
    artifact_identifier,
)


def scoped_repair_plan(issue: str) -> ScopedRepairPlan:
    scope = _scope_from_issue(issue)
    failure_class = _failure_class_from_issue(issue)
    return ScopedRepairPlan(
        scope=scope,
        failure_class=failure_class,
        strategy=_strategy_for_failure(failure_class, issue),
        message=issue,
    )


def scoped_repair_plans(issues: list[str]) -> list[JsonObject]:
    return [repair_plan_json(scoped_repair_plan(issue)) for issue in issues]


def scoped_repair_update(
    artifact: JsonObject,
    plan: ScopedRepairPlan,
    store: ContentVersionStore,
    *,
    critique: str,
    max_attempts: int,
    force_residual_failure: bool = False,
) -> ScopedRepairUpdate:
    before = store.latest(artifact_identifier(artifact)) or store.snapshot(artifact, "initial")
    if artifact.get("approved") is True:
        return _teacher_suggested_update(artifact, plan, store, before, "blocked_approved_content")
    repaired = _repair_artifact(artifact, plan, critique)
    version = store.snapshot(repaired, f"scoped repair: {plan.failure_class.value}")
    residual = force_residual_failure or max_attempts <= 1
    diff = RepairDiff(
        status="residual_issue" if residual else "changed",
        changed_path=_changed_path(plan),
        previous_hash=before.content_hash,
        next_hash=version.content_hash,
    )
    authority = "teacher_suggested" if residual else "auto_applied"
    return ScopedRepairUpdate(
        artifact=repaired,
        version=version,
        diff=diff,
        event=_event(plan, diff, authority),
        escalate_to_teacher=residual,
    )


def repair_plan_json(plan: ScopedRepairPlan) -> JsonObject:
    return {
        "artifact_id": plan.scope.artifact_id,
        "section_index": plan.scope.section_index,
        "component_index": plan.scope.component_index,
        "failure_class": plan.failure_class.value,
        "strategy": plan.strategy,
        "message": plan.message,
    }


def _teacher_suggested_update(
    artifact: JsonObject,
    plan: ScopedRepairPlan,
    store: ContentVersionStore,
    before: ContentVersion,
    status: str,
) -> ScopedRepairUpdate:
    version = store.snapshot(artifact, "teacher suggested scoped edit")
    diff = RepairDiff(
        status=status,
        changed_path=_changed_path(plan),
        previous_hash=before.content_hash,
        next_hash=version.content_hash,
    )
    return ScopedRepairUpdate(
        artifact=artifact,
        version=version,
        diff=diff,
        event=_event(plan, diff, "teacher_suggested"),
        escalate_to_teacher=True,
    )


def _repair_artifact(artifact: JsonObject, plan: ScopedRepairPlan, critique: str) -> JsonObject:
    repaired = dict(artifact)
    sections = artifact.get("sections")
    if not isinstance(sections, list) or plan.scope.section_index is None:
        metadata = _json_object(artifact.get("metadata"))
        repaired["metadata"] = {**metadata, "scoped_repair_note": critique}
        return repaired
    repaired_sections = [section for section in sections]
    section_index = plan.scope.section_index
    if section_index >= len(repaired_sections):
        return repaired
    section = _json_object(repaired_sections[section_index])
    repaired_sections[section_index] = {
        **section,
        "content": _repaired_content(section, critique),
        "repair_history": [
            *_json_objects(section.get("repair_history")),
            {"failure_class": plan.failure_class.value, "strategy": plan.strategy, "critique": critique},
        ],
    }
    repaired["sections"] = repaired_sections
    return repaired


def _repaired_content(section: JsonObject, critique: str) -> str:
    content = str(section.get("content", ""))
    return f"{content}\nRepair applied: {critique}" if content else f"Repair applied: {critique}"


def _scope_from_issue(issue: str) -> RepairScope:
    head = issue.split(":", 1)[0]
    artifact_id = head.split(".", 1)[0]
    return RepairScope(
        artifact_id=artifact_id,
        section_index=_indexed_segment(head, "sections"),
        component_index=_indexed_segment(head, "components"),
    )


def _indexed_segment(value: str, segment: str) -> int | None:
    marker = f"{segment}["
    if marker not in value:
        return None
    suffix = value.split(marker, 1)[1]
    index_text = suffix.split("]", 1)[0]
    if not index_text.isdecimal():
        return None
    return int(index_text)


def _failure_class_from_issue(issue: str) -> QualityFailureClass:
    for failure_class in QualityFailureClass:
        if failure_class.value in issue:
            return failure_class
    return QualityFailureClass.UNSUPPORTED_COMPONENT


def _strategy_for_failure(failure_class: QualityFailureClass, issue: str) -> RepairStrategy:
    if "methodology component" in issue:
        return "inject_required_component"
    match failure_class:
        case QualityFailureClass.SCHEMA_INVALID | QualityFailureClass.PLACEHOLDER_CONTENT:
            return HealingStrategy.SCHEMA_REPAIR.value
        case QualityFailureClass.ANSWER_KEY_LEAKAGE:
            return HealingStrategy.ANSWER_KEY_REPAIR.value
        case QualityFailureClass.PII_LEAKAGE:
            return HealingStrategy.PII_REMOVAL.value
        case QualityFailureClass.EXTERNAL_ASSET | QualityFailureClass.MISSING_DOCTYPE:
            return HealingStrategy.PRESENTATION_REPAIR.value
        case QualityFailureClass.MISSING_ACCESSIBILITY:
            return HealingStrategy.ACCESSIBILITY_REPAIR.value
        case QualityFailureClass.FACTUAL_UNCERTAINTY:
            return HealingStrategy.RESEARCH_ENRICHMENT.value
        case QualityFailureClass.PEDAGOGICAL_MISMATCH:
            return HealingStrategy.REPLAN_BLUEPRINT.value
        case QualityFailureClass.UNSUPPORTED_COMPONENT | QualityFailureClass.EXPORT_NOT_READY:
            return HealingStrategy.REGENERATE_ARTIFACT.value
        case unreachable:
            assert_never(unreachable)


def _changed_path(plan: ScopedRepairPlan) -> str:
    path = plan.scope.artifact_id
    if plan.scope.section_index is not None:
        path = f"{path}.sections[{plan.scope.section_index}]"
    if plan.scope.component_index is not None:
        path = f"{path}.components[{plan.scope.component_index}]" if plan.scope.section_index is None else path
    return path


def _event(plan: ScopedRepairPlan, diff: RepairDiff, authority: str) -> RepairEvent:
    diff_payload: JsonObject = {
        "status": diff["status"],
        "changed_path": diff["changed_path"],
        "previous_hash": diff["previous_hash"],
        "next_hash": diff["next_hash"],
    }
    payload: JsonObject = {
        "artifact_id": plan.scope.artifact_id,
        "failure_class": plan.failure_class.value,
        "strategy": plan.strategy,
        "authority": authority,
        "diff": diff_payload,
    }
    return {
        "event_name": "teaching_pack.content_version.created",
        "payload": payload,
    }


def _json_object(value: JsonValue | None) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _json_objects(value: JsonValue | None) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
