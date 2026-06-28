from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.quality_gates import export_readiness

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

    from common.contracts.quality import ArtifactQualityReport, ExportReadinessReport
    from services.gateway.teaching_pack_types import JsonObject, JsonValue, RunId


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
    event_name = "teaching_pack.quality.artifact_passed"
    if not report.passed:
        event_name = "teaching_pack.quality.artifact_failed"
    payload = _artifact_quality_payload(report)
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=run_id,
        event_name=event_name,
        visibility=TeachingPackEventVisibility.INTERNAL,
        payload=payload,
    ))
    return QualityEventWrite(run_id=run_id, event_name=event_name, payload=payload)


async def evaluate_export_readiness(
    session: AsyncSession,
    run_id: RunId,
    required_artifact_types: Sequence[str] = ("lesson",),
) -> ExportReadinessReport:
    snapshots = await TeachingPackSnapshotStore(session).list_run_snapshots(run_id)
    report = export_readiness(run_id, snapshots, required_artifact_types)
    event_name = "teaching_pack.export.readiness_passed"
    if not report.passed:
        event_name = "teaching_pack.export.readiness_failed"
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=run_id,
        event_name=event_name,
        visibility=TeachingPackEventVisibility.TEACHER,
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
