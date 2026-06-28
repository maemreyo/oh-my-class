from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict, assert_never

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
    approval_gate: NotRequired[JsonObject]
    teacher_approved: NotRequired[bool]
    teacher_decision: NotRequired[str]
    gate_payload: NotRequired[JsonObject]
    approved_snapshot_ids: NotRequired[list[str]]
    exported_files: NotRequired[list[str]]


def make_stage_node(stage: TeachingPackStage):
    def stage_node(state: TeachingPackState) -> TeachingPackState:
        match stage.value:
            case "setup_contract":
                update = _setup_contract(state)
            case "preplanning_search":
                update = _preplanning_search(state)
            case "planning_blueprint":
                update = _planning_blueprint(state)
            case "post_blueprint_research":
                update = _post_blueprint_research(state)
            case "artifact_workflow":
                update = _artifact_workflow(state)
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


def _planning_blueprint(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    return {
        "run_id": state["run_id"],
        "lesson_plan": {
            "topic": _topic(contract),
            "grade_level": _string_field(contract, "grade_band", "Grade 5"),
            "subject": _string_field(contract, "subject", "general"),
            "language": _string_field(contract, "instruction_language", "en"),
            "learning_objectives": [
                {"bloom_level": "understand", "description": f"Explain {_topic(contract)}."},
                {"bloom_level": "apply", "description": f"Practice {_topic(contract)} with guided tasks."},
            ],
        },
    }


def _post_blueprint_research(state: TeachingPackState) -> TeachingPackState:
    brief = state.get("research_brief", {})
    return {
        "run_id": state["run_id"],
        "research_brief": {
            **brief,
            "claims": [
                {
                    "claim": "Generated pack content is derived from the approved run contract.",
                    "verification": "contract",
                },
            ],
        },
    }


def _artifact_workflow(state: TeachingPackState) -> TeachingPackState:
    contract = state.get("contract", {})
    lesson_plan = state.get("lesson_plan", {})
    artifacts = [
        _artifact(state["run_id"], artifact_type, contract, lesson_plan)
        for artifact_type in state.get("artifact_types", _artifact_types(contract))
    ]
    return {"run_id": state["run_id"], "artifacts": artifacts}


def _render_quality(state: TeachingPackState) -> TeachingPackState:
    snapshots = [build_snapshot(state["run_id"], artifact) for artifact in state.get("artifacts", [])]
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
    return {
        "run_id": state["run_id"],
        "approval_gate": gate_payload,
        "gate_payload": response,
        "teacher_approved": action == "approve",
        "teacher_decision": action,
        "approved_snapshot_ids": snapshot_ids if action == "approve" else [],
    }


def _export_finalize(state: TeachingPackState) -> TeachingPackState:
    if not state.get("teacher_approved", False):
        return {"run_id": state["run_id"], "exported_files": []}
    snapshot_ids = state.get("approved_snapshot_ids", [])
    exported_files = [f"exports/{state['run_id']}/{snapshot_id}.html" for snapshot_id in snapshot_ids]
    return {"run_id": state["run_id"], "exported_files": exported_files}


def _complete_stage(state: TeachingPackState, stage: str) -> TeachingPackState:
    return {
        **state,
        "current_stage": stage,
        "completed_stages": [*state.get("completed_stages", []), stage],
    }


def _artifact(
    run_id: str,
    artifact_type: str,
    contract: JsonObject,
    lesson_plan: JsonObject,
) -> JsonObject:
    artifact_id = f"art-{run_id}-{artifact_type}"
    title = f"{_topic(contract)} {artifact_type.replace('_', ' ').title()}"
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "theme": "default",
        "title": title,
        "sections": [
            {
                "heading": "Learning focus",
                "body": f"{title} for {_string_field(contract, 'grade_band', 'the class')}.",
            },
            {
                "heading": "Teacher guidance",
                "body": _objective_summary(lesson_plan),
            },
        ],
        "teacher_only": {
            "answer_key": f"Review answers for {title} during teacher-led discussion.",
        },
    }


def _artifact_types(contract: JsonObject) -> list[str]:
    values = contract.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    return ["lesson", "worksheet", "quiz", "recap"]


def _topic(contract: JsonObject) -> str:
    return _string_field(contract, "topic", "Teaching Pack")


def _objective_summary(lesson_plan: JsonObject) -> str:
    objectives = lesson_plan.get("learning_objectives")
    if isinstance(objectives, list) and objectives:
        first = objectives[0]
        if isinstance(first, dict):
            return str(first.get("description", "Use this artifact in class."))
    return "Use this artifact in class."


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default

