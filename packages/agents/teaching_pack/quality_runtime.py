from __future__ import annotations

import logging

from common.contracts.artifact_workflow import ArtifactWorkflowState
from common.contracts.quality import QualityFailureClass

from packages.agents.teaching_pack.healing_runtime import heal_quality_failure
from packages.agents.teaching_pack.quality import TeachingPackQualityGateError, quality_issues
from packages.agents.teaching_pack.quality_routing import (
    pack_coherence_issues,
    render_quality_failure,
)

_log = logging.getLogger(__name__)
from packages.agents.teaching_pack.scoped_repair import scoped_repair_plans
from packages.agents.teaching_pack.snapshots import build_snapshot
from packages.agents.sub_agents.reviewer.live_quality_gate import LiveReviewerQualityGate

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from common.contracts.quality import ArtifactQualityReport
    from packages.agents.teaching_pack.ports import QualityGate

type JsonValue = str | int | float | bool | None | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]
type TeachingPackQualityValue = JsonValue | list[str]
type TeachingPackQualityState = dict[str, TeachingPackQualityValue]

_CORE_ARTIFACT_TYPES = frozenset({
    "lesson",
    "worksheet",
    "quiz",
    "drill",
    "recap",
    "flashcard_deck",
    "answer_key",
    "roadmap",
})


async def render_quality(
    state: TeachingPackQualityState,
    quality_gate: QualityGate | None = None,
) -> TeachingPackQualityState:
    artifacts = _json_objects(state.get("artifacts"))
    issues = quality_issues(artifacts)
    if issues:
        _log.warning("render_quality.layer1_issues run_id=%s artifact_count=%d issues=%r", state.get("run_id"), len(artifacts), issues)
        if pack_coherence_issues(issues):
            failure = render_quality_failure(str(state["run_id"]), issues)
            return _state_update({
                "run_id": state["run_id"],
                "quality_issues": issues,
                "quality_recovery_route": _string_field(failure, "quality_recovery_route", "repair"),
                "quality_scores": _with_scoped_repair(_json_object(failure.get("quality_scores")), issues),
            })
        raise TeachingPackQualityGateError(issues)
    passing_reports: list[ArtifactQualityReport] = []
    layer4_metadata: list[JsonObject] = []
    if quality_gate is None:
        reviewer_gate = LiveReviewerQualityGate()
        evaluated = [
            await reviewer_gate.evaluate_with_metadata(_workflow_state(str(state["run_id"]), artifact, index), artifact)
            for index, artifact in enumerate(artifacts)
            if _supports_workflow_state(artifact)
        ]
        reports = [report for report, _metadata in evaluated]
        layer4_metadata = [_json_object(metadata) for _report, metadata in evaluated]
        failed_issues = _failed_report_issues(reports)
        if failed_issues:
            failure = render_quality_failure(str(state["run_id"]), failed_issues)
            return _state_update({
                "run_id": state["run_id"],
                "quality_issues": failed_issues,
                "quality_recovery_route": _string_field(failure, "quality_recovery_route", "repair"),
                "quality_scores": _with_scoped_repair(
                    _with_layer4(_json_object(failure.get("quality_scores")), layer4_metadata),
                    failed_issues,
                ),
            })
    else:
        reports = [
            await quality_gate.evaluate(_workflow_state(str(state["run_id"]), artifact, index), artifact)
            for index, artifact in enumerate(artifacts)
            if _supports_workflow_state(artifact)
        ]
        failed_issues = _failed_report_issues(reports)
        if failed_issues:
            _log.warning("render_quality.layer2_issues run_id=%s artifact_count=%d issues=%r route=%s", state.get("run_id"), len(artifacts), failed_issues, heal_quality_failure(state, _failure_classes(reports), failed_issues).get("quality_recovery_route"))
            failure = render_quality_failure(str(state["run_id"]), failed_issues)
            healing = heal_quality_failure(state, _failure_classes(reports), failed_issues)
            return _state_update({
                "run_id": state["run_id"],
                "quality_issues": failed_issues,
                "quality_recovery_route": _string_field(healing, "quality_recovery_route", _string_field(failure, "quality_recovery_route", "repair")),
                "quality_scores": _with_scoped_repair(_json_object(failure.get("quality_scores")), failed_issues),
                **healing,
            })
        passing_reports = reports
    snapshots = [build_snapshot(str(state["run_id"]), artifact) for artifact in artifacts]
    quality_scores: JsonObject = {
        "overall": 8.0,
        "passed": True,
        "snapshot_count": len(snapshots),
    }
    if passing_reports:
        quality_scores["reports"] = [r.model_dump(mode="json") for r in passing_reports]
    if layer4_metadata:
        quality_scores["layer4_reviewer"] = layer4_metadata[0]
    return _state_update({
        "run_id": state["run_id"],
        "rendered_snapshots": snapshots,
        "quality_scores": quality_scores,
        "quality_recovery_route": None,
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


def _with_layer4(scores: JsonObject, metadata: list[JsonObject]) -> JsonObject:
    if metadata:
        return {**scores, "layer4_reviewer": metadata[0]}
    return scores


def _with_scoped_repair(scores: JsonObject, issues: list[str]) -> JsonObject:
    return {**scores, "scoped_repair_plans": scoped_repair_plans(issues)}


def _string_field(data: JsonObject, key: str, default: str) -> str:
    value = data.get(key)
    if isinstance(value, str) and value:
        return value
    return default
