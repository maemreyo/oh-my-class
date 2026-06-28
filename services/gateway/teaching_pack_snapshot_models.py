from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now

type SnapshotJsonValue = (
    str | int | float | bool | None | list[SnapshotJsonValue] | dict[str, SnapshotJsonValue]
)
type SnapshotJsonObject = dict[str, SnapshotJsonValue]


class ArtifactSnapshot(Base):
    __tablename__ = "artifact_snapshots"
    __table_args__ = (
        UniqueConstraint("content_hash", name="uq_artifact_snapshots_content_hash"),
        Index("ix_artifact_snapshots_run_id", "run_id"),
        Index("ix_artifact_snapshots_artifact_id", "artifact_id"),
        {"schema": "public"},
    )

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    html_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_json: Mapped[SnapshotJsonObject | None] = mapped_column(JSON, nullable=True)
    rendered_html: Mapped[str] = mapped_column(Text, nullable=False)
    student_rendered_html: Mapped[str] = mapped_column(Text, nullable=False)
    renderer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    template_version: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    theme_version: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    standalone_valid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
