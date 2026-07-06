from __future__ import annotations

from typing import Any

from common.contracts.component_strategy import (
    ComponentStrategyRequest,
    ResearchSignals,
)
from common.contracts.component_strategy_selector import plan_component_strategy
from common.contracts.objective_lineage import normalize_learning_objectives
from packages.agents.teaching_pack.strategy_quality import (
    ComponentStrategyGateError,
    emit_strategy_quality_events,
    pre_generation_strategy_issues,
)

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


def run_provisional_component_strategy(state: dict[str, Any]) -> dict[str, Any]:
    request = _request_from_state(state, mode="provisional", research_signals=None)
    result = plan_component_strategy(request)
    return {
        "run_id": str(state["run_id"]),
        "component_strategy_result": result.model_dump(mode="json"),
        "component_strategy_hypotheses": list(result.hypotheses),
        "component_strategy_research_questions": list(result.research_questions),
    }


def run_final_component_strategy(state: dict[str, Any]) -> dict[str, Any]:
    request = _request_from_state(state, mode="final", research_signals=_research_signals_from_state(state))
    result = plan_component_strategy(request)
    update: dict[str, Any] = {
        "run_id": str(state["run_id"]),
        "component_strategy_result": result.model_dump(mode="json"),
    }
    if result.plan is not None:
        plan = result.plan.model_dump(mode="json")
        issues = pre_generation_strategy_issues(plan)
        emit_strategy_quality_events(str(state["run_id"]), issues, phase="pre_generation")
        hard_issues = [issue for issue in issues if issue.severity == "hard"]
        if hard_issues:
            raise ComponentStrategyGateError(hard_issues)
        update["component_strategy_plan"] = plan
        update["component_strategy_summary"] = _summary_from_plan(plan)
        _emit_component_strategy_event(state, update["component_strategy_summary"], status="planned")
    else:
        _emit_component_strategy_event(state, {}, status=str(result.status))
    return update


def strategy_gate_summary(state: dict[str, Any]) -> JsonObject:
    plan = state.get("component_strategy_plan")
    if isinstance(plan, dict):
        return _summary_from_plan(plan)
    return {}


def _request_from_state(
    state: dict[str, Any],
    *,
    mode: str,
    research_signals: ResearchSignals | None,
) -> ComponentStrategyRequest:
    contract = _object(state.get("contract"))
    lesson_plan = _object(state.get("lesson_plan"))
    return ComponentStrategyRequest(
        mode=mode,
        run_id=str(state["run_id"]),
        teacher_id_hash=str(contract.get("teacher_id_hash") or contract.get("teacher_id") or "anonymous"),
        locale=str(contract.get("instruction_language") or "vi"),
        subject=str(contract.get("subject") or lesson_plan.get("subject") or "general"),
        grade_level=str(contract.get("grade_band") or lesson_plan.get("grade_level") or "Grade 5"),
        duration_minutes=_int_value(contract.get("duration_minutes"), 45),
        artifact_types=_string_tuple(state.get("artifact_types"), ("lesson",)),
        export_formats=_string_tuple(contract.get("export_formats"), ("html",)),
        objective_refs=_objective_refs(lesson_plan),
        delivery_context={"blueprint_revision_id": str(state.get("blueprint_revision_id", "bp-rev-1"))},
        assessment_intent=_assessment_intent(contract),
        research_signals=research_signals,
    )


def _research_signals_from_state(state: dict[str, Any]) -> ResearchSignals:
    brief = _object(state.get("research_brief"))
    evidence_tags = brief.get("evidence_tags")
    tags = tuple(str(tag) for tag in evidence_tags) if isinstance(evidence_tags, list) else ()
    return ResearchSignals(
        factual_risk=str(brief.get("factual_risk", "low")),
        source_confidence=str(brief.get("source_confidence", "high")),
        prerequisite_risk=str(brief.get("prerequisite_risk", "met")),
        evidence_tags=tags,
    )


def _objective_refs(lesson_plan: JsonObject) -> tuple[dict[str, str], ...]:
    objectives = lesson_plan.get("learning_objectives")
    if not isinstance(objectives, list) or not objectives:
        return ({"objective_id": "LO-1", "objective_revision": "rev-1"},)
    normalized = normalize_learning_objectives([_objective_lineage_input(_object(item)) for item in objectives])
    return tuple(
        {"objective_id": objective.objective_id, "objective_revision": objective.objective_revision}
        for objective in normalized.objectives
    )


def _objective_lineage_input(objective: JsonObject) -> dict[str, str | bool]:
    allowed = ("description", "bloom_level", "assessment_method", "importance", "assessment_intent", "objective_id", "objective_revision")
    result: dict[str, str | bool] = {key: str(objective[key]) for key in allowed if isinstance(objective.get(key), str)}
    assessable = objective.get("assessable")
    if isinstance(assessable, bool):
        result["assessable"] = assessable
    return result


def _summary_from_plan(plan: JsonObject) -> JsonObject:
    recommended = _object(plan.get("recommended"))
    sequence = recommended.get("learning_sequence")
    slots = [item for item in sequence if isinstance(item, dict)] if isinstance(sequence, list) else []
    fallback = _object(recommended.get("fallback_metadata"))
    return {
        "strategy_family_id": str(recommended.get("strategy_family_id", "")),
        "selected_learning_moves": [str(slot.get("learning_move_id", "")) for slot in slots],
        "selected_component_types": [str(slot.get("component_type", "")) for slot in slots],
        "rationale": str(plan.get("rationale_text", "")),
        "fallback_note": str(fallback.get("teacher_visible_note", "")) if fallback else "",
        "feedback_actions": [
            "prefer_component_family",
            "reject_component_family",
            "prefer_learning_move",
            "reject_learning_move",
        ],
    }


def _emit_component_strategy_event(state: dict[str, Any], summary: JsonObject, *, status: str) -> None:
    from packages.agents.events import emit_run_event

    contract = _object(state.get("contract"))
    emit_run_event(
        str(state["run_id"]),
        "component_strategy",
        {
            "run_id": str(state["run_id"]),
            "teacher_id": str(contract.get("teacher_id") or contract.get("teacher_id_hash") or "anonymous"),
            "environment": _environment_name(),
            "feature_variant": "internal_hidden",
            "status": status,
            "strategy_family_id": str(summary.get("strategy_family_id", "")),
            "selected_component_types": _string_list(summary.get("selected_component_types")),
            "fallback_used": bool(summary.get("fallback_note")),
        },
    )


def _environment_name() -> str:
    import os

    return os.getenv("APP_ENV", "development").lower()


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _assessment_intent(contract: JsonObject) -> tuple[str, ...]:
    values = contract.get("assessment_intent")
    if isinstance(values, list):
        return tuple(str(value) for value in values)
    return ()


def _string_tuple(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return default


def _object(value: object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _int_value(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return default
