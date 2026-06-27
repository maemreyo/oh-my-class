from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class ArtifactWorkflowStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    VALIDATING = "validating"
    HEALING = "healing"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ESCALATED = "escalated"


class ArtifactCheckStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ArtifactWorkflow(Base):
    __tablename__ = "artifact_workflows"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_id", name="uq_artifact_workflows_artifact"),
        Index("ix_artifact_workflows_run_id", "run_id"),
        {"schema": "public"},
    )

    workflow_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    artifact_id: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[ArtifactWorkflowStatus] = mapped_column(
        Enum(ArtifactWorkflowStatus, native_enum=False), nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contract_revision_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    research_guidance_id: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_status: Mapped[ArtifactCheckStatus] = mapped_column(
        Enum(ArtifactCheckStatus, native_enum=False), nullable=False,
    )
    judge_status: Mapped[ArtifactCheckStatus] = mapped_column(
        Enum(ArtifactCheckStatus, native_enum=False), nullable=False,
    )
    snapshot_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    snapshot_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )
