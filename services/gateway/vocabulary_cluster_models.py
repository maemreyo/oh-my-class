from __future__ import annotations

from datetime import datetime  # noqa: TC003
from enum import StrEnum

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


def _enum_values(enum_class):
    return [member.value for member in enum_class]


class VocabularyClusterWorkflowStatus(StrEnum):
    QUEUED = "queued"
    GROUNDING = "grounding"
    SYNTHESIZING = "synthesizing"
    PRACTICE_GENERATING = "practice_generating"
    VALIDATING = "validating"
    NEEDS_REVIEW = "needs_review"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    EXPORTED = "exported"


class VocabularyClusterReviewStatus(StrEnum):
    PENDING = "pending"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class VocabularyClusterEvidenceType(StrEnum):
    NORMALIZED_INPUT = "normalized_input"
    GROUNDING_SOURCES = "grounding_sources"
    GENERATED_CONTRACT_VERSION = "generated_contract_version"
    QUALITY_RESULT = "quality_result"
    TEACHER_EDIT = "teacher_edit"
    APPROVAL = "approval"
    EXPORT_REF = "export_ref"
    RETRY = "retry"


class VocabularyClusterWorkflowModel(Base):
    __tablename__ = "vocabulary_cluster_workflows"
    __table_args__ = (
        UniqueConstraint("run_id", "cluster_id", name="uq_vocabulary_cluster_workflows_cluster"),
        Index("ix_vocabulary_cluster_workflows_run_id", "run_id"),
        {"schema": "public"},
    )

    workflow_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    cluster_id: Mapped[str] = mapped_column(String(120), nullable=False)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    normalized_input: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    raw_input_span: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[VocabularyClusterWorkflowStatus] = mapped_column(
        Enum(VocabularyClusterWorkflowStatus, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_status: Mapped[VocabularyClusterReviewStatus] = mapped_column(
        Enum(VocabularyClusterReviewStatus, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    export_refs: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    snapshot_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class VocabularyClusterEvidenceModel(Base):
    __tablename__ = "vocabulary_cluster_evidence"
    __table_args__ = (
        UniqueConstraint("workflow_id", "sequence", name="uq_vocabulary_cluster_evidence_sequence"),
        Index("ix_vocabulary_cluster_evidence_run_cluster", "run_id", "cluster_id"),
        {"schema": "public"},
    )

    evidence_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(
        String(120), ForeignKey("public.vocabulary_cluster_workflows.workflow_id", ondelete="CASCADE"), nullable=False,
    )
    cluster_id: Mapped[str] = mapped_column(String(120), nullable=False)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[VocabularyClusterEvidenceType] = mapped_column(
        Enum(VocabularyClusterEvidenceType, native_enum=False, values_callable=_enum_values), nullable=False,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
