"""Persistence and staleness queries for export records (SDE-06)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from services.gateway.teaching_pack_export_models import ExportRecord

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


@dataclass(frozen=True, slots=True)
class ExportRecordCreate:
    export_id: str
    run_id: RunId
    artifact_id: str
    snapshot_id: str
    format: str
    storage_path: str
    capability_version: str | None = None


@dataclass(frozen=True, slots=True)
class ExportRecordRead:
    export_id: str
    run_id: RunId
    artifact_id: str
    snapshot_id: str
    format: str
    storage_path: str
    capability_version: str | None
    created_at: datetime


class TeachingPackExportStore:
    """Append-only store for export records.

    No update/delete method exists on purpose: an edit must never touch a
    prior export row (SDE-06 AC1). Old rows simply keep pointing at their
    (still-persisted, never-deleted) source ArtifactSnapshot.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_export_record(self, payload: ExportRecordCreate) -> ExportRecordRead:
        """#123 (OPS-10): exactly-once -- `(snapshot_id, format)` has a real
        unique constraint (migration 039). A retried completion (worker
        killed after this write but before the job is marked complete, then
        re-claimed and re-run) hits the conflict and this returns the
        original row instead of raising or silently creating a duplicate.
        The legitimate "new export" path always supplies a new snapshot_id
        (`export_manifest_service.regenerate_stale_exports` only calls this
        when the snapshot actually changed), so this never blocks a real
        re-export.
        """
        statement = pg_insert(ExportRecord).values(
            export_id=payload.export_id,
            run_id=payload.run_id,
            artifact_id=payload.artifact_id,
            snapshot_id=payload.snapshot_id,
            format=payload.format,
            storage_path=payload.storage_path,
            capability_version=payload.capability_version,
        ).on_conflict_do_nothing(
            index_elements=["snapshot_id", "format"],
        )
        await self._session.execute(statement)
        await self._session.flush()
        existing = await self._session.execute(
            select(ExportRecord).where(
                ExportRecord.snapshot_id == payload.snapshot_id,
                ExportRecord.format == payload.format,
            ),
        )
        return _read_record(existing.scalar_one())

    async def list_exports(self, run_id: RunId, artifact_id: str | None = None) -> list[ExportRecordRead]:
        statement = select(ExportRecord).where(ExportRecord.run_id == run_id)
        if artifact_id is not None:
            statement = statement.where(ExportRecord.artifact_id == artifact_id)
        statement = statement.order_by(ExportRecord.created_at.desc())
        result = await self._session.execute(statement)
        return [_read_record(record) for record in result.scalars().all()]

    async def get_latest_export(self, run_id: RunId, artifact_id: str) -> ExportRecordRead | None:
        statement = (
            select(ExportRecord)
            .where(ExportRecord.run_id == run_id, ExportRecord.artifact_id == artifact_id)
            .order_by(ExportRecord.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        record = result.scalar_one_or_none()
        return _read_record(record) if record is not None else None

    async def is_stale(self, run_id: RunId, artifact_id: str, current_snapshot_id: str | None) -> bool:
        """True when the latest export's snapshot_id lags the current head.

        No export yet -> not stale (nothing to re-export against); a
        missing/unknown current head is treated as "can't tell, not stale"
        since there's nothing newer to flag against.
        """
        if current_snapshot_id is None:
            return False
        latest = await self.get_latest_export(run_id, artifact_id)
        if latest is None:
            return False
        return latest.snapshot_id != current_snapshot_id

    async def get_latest_export_for_format(
        self, run_id: RunId, artifact_id: str, export_format: str,
    ) -> ExportRecordRead | None:
        """Latest export of one *specific* format -- `get_latest_export` picks
        the newest row across all formats, which conflates e.g. `html` and
        `gift` staleness for the same artifact; this does not."""
        statement = (
            select(ExportRecord)
            .where(
                ExportRecord.run_id == run_id,
                ExportRecord.artifact_id == artifact_id,
                ExportRecord.format == export_format,
            )
            .order_by(ExportRecord.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(statement)
        record = result.scalar_one_or_none()
        return _read_record(record) if record is not None else None

    async def stale_formats(
        self,
        run_id: RunId,
        artifact_id: str,
        current_snapshot_id: str | None,
        formats: list[str],
    ) -> list[str]:
        """Which of `formats` are stale for this artifact -- content changes must
        mark only the impacted (artifact, format) entries, not every export."""
        if current_snapshot_id is None:
            return []
        stale: list[str] = []
        for export_format in formats:
            latest = await self.get_latest_export_for_format(run_id, artifact_id, export_format)
            if latest is not None and latest.snapshot_id != current_snapshot_id:
                stale.append(export_format)
        return stale


def _read_record(record: ExportRecord) -> ExportRecordRead:
    return ExportRecordRead(
        export_id=record.export_id,
        run_id=record.run_id,
        artifact_id=record.artifact_id,
        snapshot_id=record.snapshot_id,
        format=record.format,
        storage_path=record.storage_path,
        capability_version=record.capability_version,
        created_at=record.created_at,
    )
