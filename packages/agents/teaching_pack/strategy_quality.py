from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from common.contracts.components.registry import get_entry
from packages.agents.teaching_pack.strategy_quality_events import emit_strategy_quality_events

type JsonObject = dict[str, Any]

Severity = Literal["hard", "warning"]
Phase = Literal["pre_generation", "post_generation"]

__all__ = [
    "ComponentStrategyGateError",
    "StrategyQualityIssue",
    "StrategyValidatorSpec",
    "VALIDATOR_REGISTRY",
    "emit_strategy_quality_events",
    "post_generation_strategy_issues",
    "pre_generation_strategy_issues",
]


@dataclass(frozen=True, slots=True)
class StrategyValidatorSpec:
    validator_id: str
    version: str
    phase: Phase
    category: str
    severity: Severity
    priority: int


@dataclass(frozen=True, slots=True)
class StrategyQualityIssue:
    code: str
    message: str
    severity: Severity
    location: str
    validator_id: str = "component_strategy.unknown"


VALIDATOR_REGISTRY: tuple[StrategyValidatorSpec, ...] = (
    StrategyValidatorSpec("component_strategy.slot_shape", "1.0.0", "pre_generation", "slot", "hard", 10),
    StrategyValidatorSpec("component_strategy.renderability", "1.0.0", "pre_generation", "component", "hard", 20),
    StrategyValidatorSpec("component_strategy.sequence", "1.0.0", "pre_generation", "pedagogy", "hard", 30),
    StrategyValidatorSpec("component_strategy.diversity", "1.0.0", "pre_generation", "pedagogy", "warning", 40),
    StrategyValidatorSpec("component_strategy.fill_integrity", "1.0.0", "post_generation", "lineage", "hard", 50),
    StrategyValidatorSpec("component_strategy.audience_policy", "1.0.0", "post_generation", "safety", "hard", 60),
    StrategyValidatorSpec("component_strategy.budget_adherence", "1.0.0", "post_generation", "budget", "hard", 70),
)


class ComponentStrategyGateError(RuntimeError):
    def __init__(self, issues: list[StrategyQualityIssue]) -> None:
        self.issues = issues
        super().__init__("Component strategy gate failed: " + "; ".join(issue.code for issue in issues))


def pre_generation_strategy_issues(plan: JsonObject) -> list[StrategyQualityIssue]:
    slots = _slots(plan)
    issues: list[StrategyQualityIssue] = []
    if not slots:
        return [_issue("prose_only_strategy", "Strategy has no selected typed slots.", "hard", "recommended.learning_sequence")]
    for index, slot in enumerate(slots):
        issues.extend(_slot_issues(slot, f"recommended.learning_sequence[{index}]"))
    issues.extend(_projection_issues(plan, slots))
    issues.extend(_sequence_issues(slots))
    return issues


def post_generation_strategy_issues(plan: JsonObject, artifacts: list[JsonObject]) -> list[StrategyQualityIssue]:
    issues: list[StrategyQualityIssue] = []
    slots = {str(slot.get("slot_id")): slot for slot in _slots(plan)}
    for projection in _projections(plan):
        artifact_type = str(projection.get("artifact_type", ""))
        artifact = _artifact_by_type(artifacts, artifact_type)
        ordered_slot_ids = _strings(projection.get("ordered_slot_ids"))
        if artifact is None:
            issues.append(_issue("artifact_missing_for_projection", f"Missing generated artifact {artifact_type}.", "hard", artifact_type))
            continue
        filled_ids = _filled_slot_ids(artifact)
        if filled_ids != ordered_slot_ids:
            issues.append(_issue("selected_slot_order_changed", "Generated artifact did not preserve selected slot order.", "hard", artifact_type))
        for slot_id in ordered_slot_ids:
            slot = slots.get(slot_id)
            component = _component_for_slot(artifact, slot_id)
            if slot is None:
                issues.append(_issue("slot_missing_from_strategy", f"Projection references unknown slot {slot_id}.", "hard", artifact_type))
                continue
            if component is None:
                fallback = _fallback_for_slot(artifact, slot_id)
                if fallback is None:
                    issues.append(_issue("selected_slot_not_filled", f"Selected slot {slot_id} was not filled.", "hard", artifact_type))
                elif not fallback.get("reason"):
                    issues.append(_issue("fallback_without_reason", f"Fallback for slot {slot_id} has no reason.", "hard", artifact_type))
                continue
            if component.get("type") == "paragraph":
                issues.append(_issue("prose_only_component_downgrade", f"Slot {slot_id} downgraded to prose.", "hard", artifact_type))
            if str(component.get("type")) != str(slot.get("component_type")):
                fallback = _fallback_for_slot(artifact, slot_id)
                if fallback is None:
                    issues.append(_issue("selected_component_changed", f"Slot {slot_id} changed component type.", "hard", artifact_type))
            issues.extend(_component_policy_issues(slot, component, artifact_type))
    return issues


def _slot_issues(slot: JsonObject, location: str) -> list[StrategyQualityIssue]:
    issues: list[StrategyQualityIssue] = []
    slot_id = str(slot.get("slot_id", ""))
    if not slot_id:
        issues.append(_issue("missing_slot_id", "Strategy slot is missing slot_id.", "hard", location))
    component_type = str(slot.get("component_type", ""))
    if component_type in {"", "paragraph"}:
        issues.append(_issue("prose_only_strategy", "Strategy selected a prose-only component.", "hard", location))
    try:
        entry = get_entry(component_type)
    except KeyError:
        issues.append(_issue("unsupported_component_type", f"Unsupported component type {component_type}.", "hard", location))
        entry = None
    if not str(slot.get("learning_move_id", "")):
        issues.append(_issue("missing_learning_move", "Strategy slot is missing learning_move_id.", "hard", location))
    if not _dicts(slot.get("objective_refs")):
        issues.append(_issue("missing_objective_coverage", "Strategy slot has no objective refs.", "hard", location))
    if not _strings(slot.get("target_artifacts")):
        issues.append(_issue("missing_artifact_projection", "Strategy slot has no target artifacts.", "hard", location))
    if _object(slot.get("fallback_metadata")) and not str(_object(slot.get("fallback_metadata")).get("reason_code", "")):
        issues.append(_issue("fallback_without_reason", "Strategy slot fallback metadata has no reason.", "hard", location))
    issues.extend(_budget_issues(slot, location))
    if entry is not None:
        for artifact_type in _strings(slot.get("target_artifacts")):
            if artifact_type not in entry.artifact_types:
                issues.append(_issue("artifact_component_incompatible", f"{component_type} cannot render in {artifact_type}.", "hard", location))
    return issues


def _budget_issues(slot: JsonObject, location: str) -> list[StrategyQualityIssue]:
    budget = _object(slot.get("budget"))
    required = ("ideal_time_minutes", "max_time_minutes", "ideal_item_count", "max_item_count")
    if any(not isinstance(budget.get(key), int) for key in required):
        return [_issue("invalid_slot_budget", "Strategy slot budget is incomplete.", "hard", location)]
    if int(budget["ideal_time_minutes"]) > int(budget["max_time_minutes"]):
        return [_issue("invalid_slot_budget", "Ideal time exceeds max time.", "hard", location)]
    if int(budget["ideal_item_count"]) > int(budget["max_item_count"]):
        return [_issue("invalid_slot_budget", "Ideal item count exceeds max item count.", "hard", location)]
    return []


def _projection_issues(plan: JsonObject, slots: list[JsonObject]) -> list[StrategyQualityIssue]:
    slot_ids = {str(slot.get("slot_id")) for slot in slots}
    issues: list[StrategyQualityIssue] = []
    for index, projection in enumerate(_projections(plan)):
        ordered_slot_ids = _strings(projection.get("ordered_slot_ids"))
        if not ordered_slot_ids:
            issues.append(_issue("missing_projection_slots", "Artifact projection has no ordered slots.", "hard", f"artifact_strategies[{index}]"))
        for slot_id in ordered_slot_ids:
            if slot_id not in slot_ids:
                issues.append(_issue("projection_references_unknown_slot", f"Projection references unknown slot {slot_id}.", "hard", f"artifact_strategies[{index}]"))
    return issues


def _sequence_issues(slots: list[JsonObject]) -> list[StrategyQualityIssue]:
    component_types = [str(slot.get("component_type", "")) for slot in slots]
    has_retrieval = any(component in {"question_list", "active_recall_prompt", "contrastive_pairs", "flow_step"} for component in component_types)
    if not has_retrieval:
        return [_issue("missing_retrieval_or_formative_check", "Strategy has no retrieval or formative check.", "hard", "recommended.learning_sequence")]
    if len(set(component_types)) == 1 and len(component_types) > 1:
        return [_issue("low_component_diversity", "All selected components use the same family.", "warning", "recommended.learning_sequence")]
    return []


def _component_policy_issues(slot: JsonObject, component: JsonObject, artifact_type: str) -> list[StrategyQualityIssue]:
    issues: list[StrategyQualityIssue] = []
    audience_policy = _strings(slot.get("audience_policy"))
    if "student_no_answers" in audience_policy and _contains_teacher_only_field(component):
        issues.append(_issue("teacher_only_field_on_student_surface", "Student-facing component includes teacher-only answer data.", "hard", artifact_type))
    max_items = _budget_max_items(slot)
    if max_items is not None and _component_item_count(component) > max_items:
        issues.append(_issue("slot_budget_exceeded", "Generated component exceeds selected slot budget.", "hard", artifact_type))
    for requirement in _strings(slot.get("fill_requirements")):
        if requirement and requirement.casefold() not in str(component).casefold():
            issues.append(_issue("fill_requirement_not_met", f"Generated component missed fill requirement: {requirement}.", "hard", artifact_type))
            break
    return issues


def _contains_teacher_only_field(component: JsonObject) -> bool:
    forbidden = {"answer", "answer_key", "explain", "wrong_reasons", "coaching_notes", "teacher_rationale"}
    if forbidden.intersection(component):
        return True
    questions = component.get("questions")
    return any(isinstance(question, dict) and forbidden.intersection(question) for question in questions) if isinstance(questions, list) else False


def _component_item_count(component: JsonObject) -> int:
    questions = component.get("questions")
    if isinstance(questions, list):
        return len(questions)
    items = component.get("items")
    if isinstance(items, list):
        return len(items)
    steps = component.get("steps")
    if isinstance(steps, list):
        return len(steps)
    return 1


def _budget_max_items(slot: JsonObject) -> int | None:
    budget = _object(slot.get("budget"))
    value = budget.get("max_item_count")
    if isinstance(value, int):
        return value
    return None


def _issue(code: str, message: str, severity: Severity, location: str) -> StrategyQualityIssue:
    return StrategyQualityIssue(
        code=code,
        message=message,
        severity=severity,
        location=location,
        validator_id=_validator_id_for(code),
    )


def _validator_id_for(code: str) -> str:
    if code in {"missing_slot_id", "missing_learning_move", "missing_objective_coverage", "invalid_slot_budget", "missing_artifact_projection"}:
        return "component_strategy.slot_shape"
    if code in {"unsupported_component_type", "artifact_component_incompatible", "prose_only_strategy"}:
        return "component_strategy.renderability"
    if code in {"missing_retrieval_or_formative_check", "low_component_diversity"}:
        return "component_strategy.sequence"
    if code in {"selected_slot_order_changed", "selected_slot_not_filled", "selected_component_changed", "prose_only_component_downgrade", "fallback_without_reason"}:
        return "component_strategy.fill_integrity"
    if code == "teacher_only_field_on_student_surface":
        return "component_strategy.audience_policy"
    if code in {"slot_budget_exceeded", "fill_requirement_not_met"}:
        return "component_strategy.budget_adherence"
    return "component_strategy.unknown"


def _slots(plan: JsonObject) -> list[JsonObject]:
    return _dicts(_object(plan.get("recommended")).get("learning_sequence"))


def _projections(plan: JsonObject) -> list[JsonObject]:
    return _dicts(_object(plan.get("recommended")).get("artifact_strategies"))


def _artifact_by_type(artifacts: list[JsonObject], artifact_type: str) -> JsonObject | None:
    for artifact in artifacts:
        if artifact.get("artifact_type") == artifact_type:
            return artifact
    return None


def _filled_slot_ids(artifact: JsonObject) -> list[str]:
    metadata = _object(artifact.get("metadata"))
    strategy = _object(metadata.get("component_strategy"))
    return _strings(strategy.get("slot_ids"))


def _component_for_slot(artifact: JsonObject, slot_id: str) -> JsonObject | None:
    for component in _components(artifact):
        if component.get("strategy_slot_id") == slot_id:
            return component
    return None


def _fallback_for_slot(artifact: JsonObject, slot_id: str) -> JsonObject | None:
    metadata = _object(artifact.get("metadata"))
    strategy = _object(metadata.get("component_strategy"))
    for fallback in _dicts(strategy.get("fallbacks")):
        if fallback.get("slot_id") == slot_id:
            return fallback
    return None


def _components(artifact: JsonObject) -> list[JsonObject]:
    components: list[JsonObject] = []
    for section in _dicts(artifact.get("sections")):
        components.extend(_dicts(section.get("components")))
    return components


def _object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _dicts(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]
