from __future__ import annotations

from common.contracts.quality import QualityFailureClass
from packages.agents.healing.orchestrator import HealingOrchestrator

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]
type HealingUpdate = dict[str, JsonValue | list[str]]

_PLANNING_FAILURES = frozenset({
    QualityFailureClass.PEDAGOGICAL_MISMATCH,
    QualityFailureClass.FACTUAL_UNCERTAINTY,
})


def heal_quality_failure(
    state: dict[str, JsonValue | list[str]],
    failure_classes: list[QualityFailureClass],
    issues: list[str],
) -> HealingUpdate:
    fail_type = _fail_type(failure_classes)
    fail_context: JsonObject = {"errors": [*issues]}
    healing_state: dict[str, JsonValue] = {
        "fail_count": _int_field(state, "fail_count"),
        "fail_type": fail_type,
        "fail_layer": "quality",
        "fail_context": fail_context,
    }
    generation_model = state.get("generation_model")
    if isinstance(generation_model, str) and generation_model:
        healing_state["generation_model"] = generation_model
    healing = HealingOrchestrator().heal(healing_state)
    route = _route_for_healing(healing, failure_classes)
    return _healing_update({
        **healing,
        "quality_recovery_route": route,
    })


def _route_for_healing(
    healing: dict[str, JsonValue],
    failure_classes: list[QualityFailureClass],
) -> str:
    if healing.get("escalate") is True:
        return "teacher_approval"
    if healing.get("healing_strategy") == "replan":
        return "planning_blueprint"
    if any(failure_class in _PLANNING_FAILURES for failure_class in failure_classes):
        return "planning_blueprint"
    return "artifact_workflow"


def _fail_type(failure_classes: list[QualityFailureClass]) -> str:
    if QualityFailureClass.SCHEMA_INVALID in failure_classes:
        return "validation"
    if QualityFailureClass.FACTUAL_UNCERTAINTY in failure_classes:
        return "content"
    return "score"


def _int_field(state: dict[str, JsonValue | list[str]], key: str) -> int:
    value = state.get(key)
    if isinstance(value, int):
        return value
    return 0


def _healing_update(value: dict[str, JsonValue]) -> HealingUpdate:
    return {key: item for key, item in value.items()}
