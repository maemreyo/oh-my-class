from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class ExportRecord(Base):
    """One row per exported file, pinned to the snapshot it was built from.

    SDE-06: rows are append-only -- an edit (new ArtifactSnapshot row) never
    updates or deletes an ExportRecord, so older exports stay reachable and
    the "re-export needed" staleness check is just a snapshot_id comparison
    against the artifact's current head (see teaching_pack_export_store.py).
    """

    __tablename__ = "export_records"
    __table_args__ = (
        Index("ix_export_records_run_id", "run_id"),
        Index("ix_export_records_artifact_id", "artifact_id"),
        Index("ix_export_records_snapshot_id", "snapshot_id"),
        {"schema": "public"},
    )

    export_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.artifact_snapshots.snapshot_id", ondelete="CASCADE"),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    capability_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
