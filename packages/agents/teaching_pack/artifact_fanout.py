from __future__ import annotations

from typing import Any, Final

from langgraph.types import Send

from common.contracts.dependency_plan import DEFAULT_DEPENDENCY_PLAN
from common.contracts.grade_band import GradeBand, grade_band_for_label
from packages.agents.teaching_pack.artifact_fanout_helpers import (
    any_json_object,
    json_object,
    json_objects,
    skipped_dependents,
    string_field,
    string_value,
    with_dependents,
)
from packages.agents.teaching_pack.config import TeachingPackConfig
from packages.agents.teaching_pack.features import artifact_send_fanout_v1_enabled
from packages.agents.teaching_pack.generate_one_artifact import GenerateOneArtifactPayload
from packages.agents.teaching_pack.reducers import (
    current_generation_artifact_references,
    current_generation_workflow_states,
)
from packages.agents.teaching_pack.scoped_regeneration import (
    rejected_artifact_types,
)

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, Any]

GENERATE_ONE_ARTIFACT_NODE: Final = "generate_one_artifact"
RENDER_QUALITY_NODE: Final = "render_quality"
# #464: the wave/dependency structure is now the typed, validated
# `DependencyPlan` contract (common/contracts/dependency_plan.py) instead of
# bare module-level tuples -- same ADR-053 default plan, now with cycle/
# forward-dependency/unknown-node validation enforced at construction.
_WAVES: Final[tuple[tuple[str, ...], ...]] = DEFAULT_DEPENDENCY_PLAN.waves
_DEPENDENCIES: Final[dict[str, tuple[str, ...]]] = DEFAULT_DEPENDENCY_PLAN.dependencies


def coordinate_artifact_fanout(state: JsonObject) -> JsonObject:
    generation_revision = _next_generation_revision(state)
    generation_id = _generation_id(state, generation_revision)
    requested_types = _requested_types(state)
    current_wave_index = _current_wave_index(state)
    scoped_types = _scoped_generation_types(state)
    current_states = current_generation_workflow_states(
        json_objects(state.get("artifact_workflow_states")),
        generation_id,
    )
    current_references = current_generation_artifact_references(
        json_objects(state.get("artifact_references")),
        generation_id,
    )
    preserved_references = [
        reference
        for reference in json_objects(state.get("artifact_references"))
        if str(reference.get("artifact_type", "")) not in scoped_types
    ] if scoped_types else []
    references = [*preserved_references, *current_references]
    update: JsonObject = {
        "run_id": str(state["run_id"]),
        "artifact_generation_id": generation_id,
        "artifact_generation_revision": generation_revision,
        "artifact_wave_index": current_wave_index,
        "artifact_fanout_complete": False,
        "artifact_references": references,
    }
    if scoped_types:
        update["artifact_regeneration_scope"] = {
            "mode": "type_scoped",
            "artifact_types": scoped_types,
        }
    current_wave = _wave_at(requested_types, current_wave_index)
    if not current_wave:
        return {**update, "artifact_fanout_complete": True}
    completed_types = _completed_types(current_states)
    if not set(current_wave).issubset(completed_types):
        return update
    failed_types = _failed_types(current_states)
    skipped_states = skipped_dependents(generation_id, requested_types, failed_types, _DEPENDENCIES)
    if skipped_states:
        update["artifact_fanout_complete"] = True
        update["artifact_fanout_blocked"] = True
        update["artifact_workflow_states"] = skipped_states
        return update
    next_wave_index = _next_wave_index(requested_types, current_wave_index)
    if next_wave_index is None:
        return {**update, "artifact_wave_index": current_wave_index, "artifact_fanout_complete": True}
    return {**update, "artifact_wave_index": next_wave_index}


def route_after_artifact_workflow(state: JsonObject) -> str | list[Send]:
    if not artifact_send_fanout_v1_enabled() or bool(state.get("artifact_fanout_complete", False)):
        return RENDER_QUALITY_NODE
    generation_id = _generation_id(state, _generation_revision(state))
    wave = _wave_at(_requested_types(state), _current_wave_index(state))
    if not wave:
        return RENDER_QUALITY_NODE
    current_states = current_generation_workflow_states(
        json_objects(state.get("artifact_workflow_states")),
        generation_id,
    )
    completed_types = _completed_types(current_states)
    return [
        Send(GENERATE_ONE_ARTIFACT_NODE, _payload(state, generation_id, artifact_type))
        for artifact_type in wave
        if artifact_type not in completed_types
    ][:_artifact_parallelism_cap()] or RENDER_QUALITY_NODE


def _payload(state: JsonObject, generation_id: str, artifact_type: str) -> GenerateOneArtifactPayload:
    contract = json_object(state.get("contract"))
    return {
        "run_id": str(state["run_id"]),
        "artifact_generation_id": generation_id,
        "artifact_type": artifact_type,
        "lesson_plan": any_json_object(state.get("lesson_plan")),
        "research_brief": any_json_object(state.get("research_brief")),
        "theme": string_field(contract, "theme", "default"),
        "revision_feedback": string_value(state.get("revision_feedback")),
        "dependency_artifact_references": json_objects(state.get("artifact_references")),
        "subject": string_field(contract, "subject", "general"),
        "grade_band": _grade_band_value(contract),
    }


def _grade_band_value(contract: JsonObject) -> str:
    # #464: threads a real GradeBand into GenerateOneArtifactPayload for
    # content_coverage_resolution.resolve_content_coverage -- stored as its
    # plain `.value` string (JSON-safe for the LangGraph checkpoint), not the
    # GradeBand enum instance itself.
    grade_level = string_field(contract, "grade_band", "Grade 5")
    band = grade_band_for_label(grade_level)
    return (band or GradeBand.GRADES_3_5).value


def _generation_revision(state: JsonObject) -> int:
    value = state.get("artifact_generation_revision")
    if isinstance(value, int) and value > 0:
        return value
    return 1


def _next_generation_revision(state: JsonObject) -> int:
    revision = _generation_revision(state)
    if _needs_new_generation_cycle(state):
        return revision + 1
    return revision


def _generation_id(state: JsonObject, revision: int) -> str:
    existing = state.get("artifact_generation_id")
    if isinstance(existing, str) and existing and revision == _generation_revision(state):
        return existing
    expected = f"{state['run_id']}:artifact:{revision}"
    if isinstance(existing, str) and existing == expected:
        return existing
    return expected


def _current_wave_index(state: JsonObject) -> int:
    requested_types = _requested_types(state)
    if _needs_new_generation_cycle(state):
        for index, _wave in enumerate(_WAVES):
            if _wave_at(requested_types, index):
                return index
    value = state.get("artifact_wave_index")
    if isinstance(value, int) and value >= 0:
        return value
    for index, _wave in enumerate(_WAVES):
        if _wave_at(requested_types, index):
            return index
    return 0


def _requested_types(state: JsonObject) -> list[str]:
    scoped_types = _scoped_generation_types(state)
    if scoped_types:
        return scoped_types
    values = state.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    contract = json_object(state.get("contract"))
    contract_values = contract.get("artifact_types")
    if isinstance(contract_values, list) and contract_values:
        return [str(value) for value in contract_values]
    return ["lesson", "worksheet", "quiz", "drill", "slide_deck"]


def _needs_new_generation_cycle(state: JsonObject) -> bool:
    if not bool(state.get("artifact_fanout_complete", False)):
        return False
    if _rejected_generation_types(state):
        return True
    return state.get("quality_recovery_route") == "artifact_workflow"


def _scoped_generation_types(state: JsonObject) -> list[str]:
    existing_scope = _recorded_scope_types(state)
    if existing_scope:
        return existing_scope
    return _rejected_generation_types(state)


def _rejected_generation_types(state: JsonObject) -> list[str]:
    rejected_types = rejected_artifact_types(
        json_objects(state.get("artifact_references")),
        json_object(state.get("gate_payload")),
    )
    if not rejected_types:
        return []
    return with_dependents(rejected_types, _all_requested_types(state), _DEPENDENCIES)


def _recorded_scope_types(state: JsonObject) -> list[str]:
    scope = state.get("artifact_regeneration_scope")
    if not isinstance(scope, dict):
        return []
    if scope.get("mode") != "type_scoped":
        return []
    artifact_types = scope.get("artifact_types")
    if not isinstance(artifact_types, list):
        return []
    return [str(artifact_type) for artifact_type in artifact_types]


def _all_requested_types(state: JsonObject) -> list[str]:
    values = state.get("artifact_types")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    contract = json_object(state.get("contract"))
    contract_values = contract.get("artifact_types")
    if isinstance(contract_values, list) and contract_values:
        return [str(value) for value in contract_values]
    return ["lesson", "worksheet", "quiz", "drill", "slide_deck"]


def _wave_at(requested_types: list[str], wave_index: int) -> list[str]:
    if wave_index >= len(_WAVES):
        return []
    requested = set(requested_types)
    return [artifact_type for artifact_type in _WAVES[wave_index] if artifact_type in requested]


def _next_wave_index(requested_types: list[str], wave_index: int) -> int | None:
    next_index = wave_index + 1
    while next_index < len(_WAVES):
        if _wave_at(requested_types, next_index):
            return next_index
        next_index += 1
    return None


def _completed_types(states: list[JsonObject]) -> set[str]:
    return {str(state.get("artifact_type", "")) for state in states if state.get("status") in {"passed", "failed", "skipped"}}


def _artifact_parallelism_cap() -> int:
    return TeachingPackConfig().default_artifact_parallelism


def _failed_types(states: list[JsonObject]) -> set[str]:
    return {str(state.get("artifact_type", "")) for state in states if state.get("status") == "failed"}
