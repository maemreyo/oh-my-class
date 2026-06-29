from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, assert_never

from packages.agents.teaching_pack.artifacts import normalize_generated_artifacts
from packages.agents.teaching_pack.quality import TeachingPackQualityGateError, quality_issues
from packages.agents.teaching_pack.quality_routing import (
    pack_coherence_issues,
    render_quality_failure,
)
from packages.agents.teaching_pack.scoped_regeneration import (
    merge_regenerated_artifacts,
    rejected_artifact_types,
    scoped_rejections,
)
from packages.agents.teaching_pack.snapshots import build_snapshot

if TYPE_CHECKING:
    from packages.agents.teaching_pack.stages import TeachingPackStage

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class TeachingPackState(TypedDict):
    run_id: str
    contract: NotRequired[JsonObject]
    current_stage: NotRequired[str]
    completed_stages: NotRequired[list[str]]
    research_brief: NotRequired[JsonObject]
    lesson_plan: NotRequired[JsonObject]
    artifact_types: NotRequired[list[str]]
    artifacts: NotRequired[list[JsonObject]]
    rendered_snapshots: NotRequired[list[JsonObject]]
    quality_scores: NotRequired[JsonObject]
    quality_issues: NotRequired[list[str]]
    quality_recovery_route: NotRequired[str]
    approval_gate: NotRequired[JsonObject]
    teacher_approved: NotRequired[bool]
    teacher_decision: NotRequired[str]
    gate_payload: NotRequired[JsonObject]
    revision_feedback: NotRequired[str]
    approved_snapshot_ids: NotRequired[list[str]]
    exported_files: NotRequired[list[str]]


def make_stage_node(stage: TeachingPackStage):
    async def stage_node(state: TeachingPackState) -> TeachingPackState:
        match stage.value:
            case "setup_contract":
                update = _setup_contract(state)
            case "preplanning_search":
                update = _preplanning_search(state)
            case "planning_blueprint":
                update = await _planning_blueprint(state)
            case "post_blueprint_research":
                update = await _post_blueprint_research(state)
            case "artifact_workflow":
                update = await _artifact_workflow(state)
            case "render_quality":
                update = _render_quality(state)
            case "teacher_approval":
                update = _teacher_approval(state)
            case "export_finalize":
                update = _export_finalize(state)
            case unreachable:
                assert_never(unreachable)
        return _complete_stage({**state, **update}, stage.value)

    stage_node.__name__ = stage.value
    return stage_node


def _setup_contract(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    artifact_types = _artifact_types(contract)
    return {
        "run_id": state["run_id"],
        "contract": contract,
        "artifact_types": artifact_types,
    }


def _preplanning_search(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    return {
        "run_id": state["run_id"],
        "research_brief": {
            "policy": _string_field(contract, "research_policy", "standard"),
            "topic": _topic(contract),
            "sources": [
                {
                    "title": "Teacher-provided lesson context",
                    "summary": _topic(contract),
                    "source_type": "contract",
                },
            ],
        },
    }


async def _planning_blueprint(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    from packages.agents.sub_agents.planner.nodes import planner_node

    result = await planner_node({
        "raw_request": _string_field(contract, "raw_request", _topic(contract)),
        "class_info": _class_info(contract),
        "run_id": state["run_id"],
        "current_step": 3,
        "lesson_plan": None,
    })
    return {"run_id": state["run_id"], "lesson_plan": _json_object(result.get("lesson_plan"))}


async def _post_blueprint_research(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    from packages.agents.sub_agents.researcher.nodes import researcher_node

    result = await researcher_node({
        "lesson_plan": state.get("lesson_plan", {}),
        "research_policy": _string_field(contract, "research_policy", "standard"),
        "run_id": state["run_id"],
        "current_step": 7,
        "research_bundle": state.get("research_brief", {}),
    })
    return {"run_id": state["run_id"], "research_brief": _json_object(result.get("research_bundle"))}


async def _artifact_workflow(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    from packages.agents.sub_agents.content_creator.nodes import content_creator_node

    artifact_types = _artifact_types_for_generation(state, contract)
    result = await content_creator_node({
        "lesson_plan": state.get("lesson_plan", {}),
        "research_bundle": state.get("research_brief", {}),
        "artifact_types": artifact_types,
        "theme": _string_field(contract, "theme", "default"),
        "run_id": state["run_id"],
        "current_step": 8,
        "artifacts": None,
        "revision_feedback": state.get("revision_feedback", ""),
    })
    generated = normalize_generated_artifacts(result.get("artifacts", []), artifact_types)
    artifacts = _merge_regenerated_artifacts(state, generated)
    return {"run_id": state["run_id"], "artifacts": artifacts}


def _render_quality(state: TeachingPackState) -> TeachingPackState:
    artifacts = state.get("artifacts", [])
    issues = quality_issues(artifacts)
    if issues:
        if pack_coherence_issues(issues):
            return render_quality_failure(state["run_id"], issues)
        raise TeachingPackQualityGateError(issues)
    snapshots = [build_snapshot(state["run_id"], artifact) for artifact in artifacts]
    return {
        "run_id": state["run_id"],
        "rendered_snapshots": snapshots,
        "quality_scores": {
            "overall": 8.0,
            "passed": True,
            "snapshot_count": len(snapshots),
        },
    }

def _teacher_approval(state: TeachingPackState) -> TeachingPackState:
    from langgraph.types import interrupt

    snapshot_ids = [str(snapshot["snapshot_id"]) for snapshot in state.get("rendered_snapshots", [])]
    artifacts = state.get("artifacts", [])
    gate_payload: JsonObject = {
        "gate": "content_approval",
        "gate_name": "content_approval",
        "snapshot_ids": snapshot_ids,
        "rendered_snapshots": state.get("rendered_snapshots", []),
        "artifacts": artifacts,
        "quality_scores": state.get("quality_scores", {}),
        "run_id": state["run_id"],
    }
    response = interrupt(gate_payload)
    action = _string_field(response, "action", "reject")
    feedback = _string_field(response, "feedback", "")
    return {
        "run_id": state["run_id"],
        "approval_gate": gate_payload,
        "gate_payload": response,
        "teacher_approved": action == "approve",
        "teacher_decision": action,
        "revision_feedback": feedback,
        "approved_snapshot_ids": snapshot_ids if action == "approve" else [],
    }


def _export_finalize(state: TeachingPackState) -> TeachingPackState:
    if not state.get("teacher_approved", False):
        return {"run_id": state["run_id"], "exported_files": []}
    snapshot_ids = state.get("approved_snapshot_ids", [])
    exported_files = [f"exports/{state['run_id']}/{snapshot_id}.html" for snapshot_id in snapshot_ids]
    return {"run_id": state["run_id"], "exported_files": exported_files}


def route_after_teacher_approval(state: TeachingPackState) -> str:
    if state.get("teacher_approved", False):
        return "export_finalize"
    if _scoped_rejections(state):
        return "artifact_workflow"
    return "export_finalize"


def _complete_stage(state: TeachingPackState, stage: str) -> TeachingPackState:
    return {
        **state,
        "current_stage": stage,
        "completed_stages": [*state.get("completed_stages", []), stage],
    }


def _artifact_types(contract: JsonObject) -> list[str]:
    values = contract.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    return ["lesson", "worksheet", "quiz", "recap"]


def _artifact_types_for_generation(state: TeachingPackState, contract: JsonObject) -> list[str]:
    rejected_types = rejected_artifact_types(
        state.get("artifacts", []),
        state.get("gate_payload", {}),
    )
    if rejected_types:
        return rejected_types
    return state.get("artifact_types", _artifact_types(contract))


def _merge_regenerated_artifacts(
    state: TeachingPackState,
    generated: list[JsonObject],
) -> list[JsonObject]:
    return merge_regenerated_artifacts(
        state.get("artifacts", []),
        state.get("gate_payload", {}),
        generated,
    )


def _scoped_rejections(state: TeachingPackState) -> list[JsonObject]:
    return scoped_rejections(state.get("artifacts", []), state.get("gate_payload", {}))


def _topic(contract: JsonObject) -> str:
    return _string_field(contract, "topic", "Teaching Pack")


def _class_info(contract: JsonObject) -> JsonObject:
    return {
        "topic": _topic(contract),
        "grade": _grade_value(contract),
        "grade_band": _string_field(contract, "grade_band", "Grade 5"),
        "subject": _string_field(contract, "subject", "general"),
        "language": _string_field(contract, "instruction_language", "en"),
        "student_count": contract.get("student_count", 30),
    }


def _grade_value(contract: JsonObject) -> JsonValue:
    value = contract.get("grade")
    if isinstance(value, int | str):
        return value
    grade_band = _string_field(contract, "grade_band", "Grade 5")
    parts = grade_band.split()
    if parts and parts[-1].isdigit():
        return int(parts[-1])
    return 5


def _json_object(value: JsonValue | object) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default
