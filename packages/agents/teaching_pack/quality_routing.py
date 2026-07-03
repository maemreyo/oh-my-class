from __future__ import annotations

from typing import TypedDict

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class QualityRecoveryState(TypedDict, total=False):
    quality_recovery_route: str


def render_quality_failure(run_id: str, issues: list[str]) -> JsonObject:
    quality_scores: JsonObject = {
        "overall": 0.0,
        "passed": False,
        "issue_count": len(issues),
    }
    return {
        "run_id": run_id,
        "quality_issues": [*issues],
        "quality_recovery_route": quality_recovery_route(issues),
        "quality_scores": quality_scores,
    }


def route_after_render_quality(state: QualityRecoveryState) -> str:
    route = state.get("quality_recovery_route")
    match route:
        case "planning_blueprint":
            return "planning_blueprint"
        case "post_blueprint_research":
            return "post_blueprint_research"
        case "artifact_workflow":
            return "artifact_workflow"
        case "teacher_approval":
            return "teacher_approval"
        case None:
            return "compliance_gate"
        case _:
            return "artifact_workflow"


def pack_coherence_issues(issues: list[str]) -> list[str]:
    return [issue for issue in issues if issue.startswith("pack.coherence:")]


def quality_recovery_route(issues: list[str]) -> str:
    joined = " ".join(issues)
    if "factual_uncertainty" in joined:
        return "post_blueprint_research"
    if "not_aligned_with_objectives" in joined or "vietnamese_difficulty" in joined:
        return "planning_blueprint"
    return "artifact_workflow"
