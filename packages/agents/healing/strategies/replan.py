from __future__ import annotations

from typing import Any, Final


_UPSTREAM_REPLAN_STAGES: Final = frozenset({"planning_blueprint", "post_blueprint_research"})
_DEPENDENT_TYPES: Final = {
    "lesson": frozenset({"worksheet", "quiz", "drill", "recap"}),
    "quiz": frozenset({"recap"}),
}


def apply(state: dict[str, Any], fail_count: int) -> dict[str, Any]:
    fail_context = _json_object(state.get("fail_context"))
    stage = _string_value(fail_context.get("stage") or fail_context.get("current_stage"))
    if stage in _UPSTREAM_REPLAN_STAGES:
        return _full_replan(fail_count, stage)
    failed_artifact_id = _string_value(fail_context.get("artifact_id"))
    if failed_artifact_id is None:
        return _full_replan(fail_count, "artifact_workflow")
    return _scoped_replan(state, fail_count, failed_artifact_id)


def _full_replan(fail_count: int, route: str) -> dict[str, Any]:
    return {
        "fail_count": fail_count,
        "healing_strategy": "replan",
        "artifact_chunks": None,
        "artifacts": None,
        "artifact_workflow_states": None,
        "rendered_snapshots": None,
        "quality_scores": None,
        "quality_issues": None,
        "quality_recovery_route": route,
        "healing_note": f"Full regeneration triggered at {route} after 3 failed attempts",
    }


def _scoped_replan(
    state: dict[str, Any],
    fail_count: int,
    failed_artifact_id: str,
) -> dict[str, Any]:
    clear_ids = _clear_artifact_ids(state, failed_artifact_id)
    return {
        "fail_count": fail_count,
        "healing_strategy": "replan",
        "artifact_chunks": _without_artifacts(state.get("artifact_chunks"), clear_ids),
        "artifacts": _without_artifacts(state.get("artifacts"), clear_ids),
        "artifact_workflow_states": _without_artifacts(state.get("artifact_workflow_states"), clear_ids),
        "rendered_snapshots": _without_artifacts(state.get("rendered_snapshots"), clear_ids),
        "quality_scores": _without_quality_reports(state.get("quality_scores"), clear_ids),
        "quality_issues": None,
        "quality_recovery_route": "artifact_workflow",
        "healing_context": {"artifact_ids": sorted(clear_ids)},
        "healing_note": f"Scoped regeneration for {failed_artifact_id} and downstream dependents",
    }


def _clear_artifact_ids(state: dict[str, Any], failed_artifact_id: str) -> set[str]:
    failed_type = _artifact_type(state, failed_artifact_id)
    clear_types = {failed_type, *_DEPENDENT_TYPES.get(failed_type, frozenset())}
    return {
        artifact_id
        for artifact_id, artifact_type in _artifact_id_types(state)
        if artifact_id == failed_artifact_id or artifact_type in clear_types
    }


def _artifact_type(state: dict[str, Any], artifact_id: str) -> str:
    for candidate_id, artifact_type in _artifact_id_types(state):
        if candidate_id == artifact_id:
            return artifact_type
    return ""


def _artifact_id_types(state: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    pairs: list[tuple[str, str]] = []
    for key in ("artifact_chunks", "artifacts", "artifact_workflow_states", "rendered_snapshots"):
        for item in _json_objects(state.get(key)):
            artifact_id = _string_value(item.get("artifact_id"))
            artifact_type = _string_value(item.get("artifact_type"))
            if artifact_id is not None and artifact_type is not None:
                pairs.append((artifact_id, artifact_type))
    return tuple(pairs)


def _without_artifacts(value: Any, clear_ids: set[str]) -> list[dict[str, Any]] | None:
    items = _json_objects(value)
    if not items:
        return None
    return [item for item in items if item.get("artifact_id") not in clear_ids]


def _without_quality_reports(value: Any, clear_ids: set[str]) -> dict[str, Any] | None:
    scores = _json_object(value)
    if not scores:
        return None
    reports = _json_objects(scores.get("reports"))
    if not reports:
        return scores
    return {**scores, "reports": [report for report in reports if report.get("artifact_id") not in clear_ids]}


def _json_objects(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, dict))


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _string_value(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
