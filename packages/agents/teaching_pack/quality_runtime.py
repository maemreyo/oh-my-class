from __future__ import annotations

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import QualityFailureClass

from packages.agents.teaching_pack.healing_runtime import heal_quality_failure
from packages.agents.teaching_pack.quality import TeachingPackQualityGateError, quality_issues
from packages.agents.teaching_pack.quality_routing import (
    pack_coherence_issues,
    render_quality_failure,
)
from packages.agents.teaching_pack.snapshots import build_snapshot

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.contracts.quality import ArtifactQualityReport
    from packages.agents.teaching_pack.ports import QualityGate

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]
type TeachingPackQualityValue = JsonValue | list[str]
type TeachingPackQualityState = dict[str, TeachingPackQualityValue]

_CORE_ARTIFACT_TYPES = frozenset({"lesson", "worksheet", "quiz", "drill", "recap"})


async def render_quality(
    state: TeachingPackQualityState,
    quality_gate: QualityGate | None = None,
) -> TeachingPackQualityState:
    artifacts = _json_objects(state.get("artifacts"))
    issues = quality_issues(artifacts)
    if issues:
        if pack_coherence_issues(issues):
            failure = render_quality_failure(str(state["run_id"]), issues)
            return _state_update({
                "run_id": state["run_id"],
                "quality_issues": issues,
                "quality_recovery_route": _string_field(failure, "quality_recovery_route", "repair"),
                "quality_scores": _json_object(failure.get("quality_scores")),
            })
        raise TeachingPackQualityGateError(issues)
    if quality_gate is not None:
        reports = [
            await quality_gate.evaluate(_workflow_state(str(state["run_id"]), artifact, index))
            for index, artifact in enumerate(artifacts)
            if _supports_workflow_state(artifact)
        ]
        failed_issues = _failed_report_issues(reports)
        if failed_issues:
            failure = render_quality_failure(str(state["run_id"]), failed_issues)
            healing = heal_quality_failure(state, _failure_classes(reports), failed_issues)
            return _state_update({
                "run_id": state["run_id"],
                "quality_issues": failed_issues,
                "quality_recovery_route": _string_field(healing, "quality_recovery_route", _string_field(failure, "quality_recovery_route", "repair")),
                "quality_scores": _json_object(failure.get("quality_scores")),
                **healing,
            })
    snapshots = [build_snapshot(str(state["run_id"]), artifact) for artifact in artifacts]
    return _state_update({
        "run_id": state["run_id"],
        "rendered_snapshots": snapshots,
        "quality_scores": {
            "overall": 8.0,
            "passed": True,
            "snapshot_count": len(snapshots),
        },
    })


def _state_update(value: TeachingPackQualityState) -> TeachingPackQualityState:
    return value


def _workflow_state(run_id: str, artifact: JsonObject, index: int) -> ArtifactWorkflowState:
    artifact_type = str(artifact.get("artifact_type", "lesson"))
    return ArtifactWorkflowState(
        workflow_id=f"{run_id}-quality-{index}",
        run_id=run_id,
        artifact_id=str(artifact.get("artifact_id", f"artifact-{index}")),
        artifact_type=artifact_type,
        status="validating",
        attempts=0,
        contract_revision_id=1,
        research_guidance_id="render-quality",
    )


def _supports_workflow_state(artifact: JsonObject) -> bool:
    return str(artifact.get("artifact_type", "")) in _CORE_ARTIFACT_TYPES


def _failed_report_issues(reports: list[ArtifactQualityReport]) -> list[str]:
    issues: list[str] = []
    for report in reports:
        if report.passed:
            continue
        issues.extend(f"{issue.location}: {issue.failure_class.value}: {issue.message}" for issue in report.issues)
    return issues


def _failure_classes(reports: list[ArtifactQualityReport]) -> list[QualityFailureClass]:
    return [issue.failure_class for report in reports for issue in report.issues if not report.passed]


def _json_objects(value: TeachingPackQualityValue | None) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _json_object(value: JsonValue | None) -> JsonObject:
    if isinstance(value, dict):
        return value
    return {}


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default
