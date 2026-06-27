from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.gateway.pipeline_v2_models import PipelineV2EventVisibility
from services.gateway.pipeline_v2_snapshot_store import PipelineV2SnapshotStore
from services.gateway.pipeline_v2_store import PipelineV2EventCreate, PipelineV2RunStore
from services.gateway.quality_gates import export_readiness

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from common.contracts.quality import ArtifactQualityReport, ExportReadinessReport
    from services.gateway.pipeline_v2_types import JsonObject, JsonValue, RunId


@dataclass(frozen=True, slots=True)
class QualityEventWrite:
    run_id: RunId
    event_name: str
    payload: JsonObject


async def write_artifact_quality_event(
    session: AsyncSession,
    run_id: RunId,
    report: ArtifactQualityReport,
) -> QualityEventWrite:
    event_name = "pipeline_v2.quality.artifact_passed"
    if not report.passed:
        event_name = "pipeline_v2.quality.artifact_failed"
    payload = _artifact_quality_payload(report)
    await PipelineV2RunStore(session).write_event(PipelineV2EventCreate(
        run_id=run_id,
        event_name=event_name,
        visibility=PipelineV2EventVisibility.INTERNAL,
        payload=payload,
    ))
    return QualityEventWrite(run_id=run_id, event_name=event_name, payload=payload)


async def evaluate_export_readiness(
    session: AsyncSession,
    run_id: RunId,
    required_artifact_types: Sequence[str] = ("lesson",),
) -> ExportReadinessReport:
    snapshots = await PipelineV2SnapshotStore(session).list_run_snapshots(run_id)
    report = export_readiness(run_id, snapshots, required_artifact_types)
    event_name = "pipeline_v2.export.readiness_passed"
    if not report.passed:
        event_name = "pipeline_v2.export.readiness_failed"
    await PipelineV2RunStore(session).write_event(PipelineV2EventCreate(
        run_id=run_id,
        event_name=event_name,
        visibility=PipelineV2EventVisibility.TEACHER,
        payload=_export_readiness_payload(report),
    ))
    return report


def _artifact_quality_payload(report: ArtifactQualityReport) -> JsonObject:
    return {
        "artifact_id": report.artifact_id,
        "artifact_type": report.artifact_type,
        "passed": report.passed,
        "issues": _issues_payload(report.issues),
    }


def _export_readiness_payload(report: ExportReadinessReport) -> JsonObject:
    return {
        "passed": report.passed,
        "approved_snapshot_ids": list(report.approved_snapshot_ids),
        "issues": _issues_payload(report.issues),
    }


def _issues_payload(issues) -> list[JsonValue]:
    return [
        {
            "failure_class": issue.failure_class.value,
            "location": issue.location,
            "message": issue.message,
            "hard_block": issue.hard_block,
        }
        for issue in issues
    ]
