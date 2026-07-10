"""Append-only persistence models for canonical V2 artifact documents."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now

type ArtifactDocumentJsonValue = (
    str | int | float | bool | None | list[ArtifactDocumentJsonValue] | dict[str, ArtifactDocumentJsonValue]
)
type ArtifactDocumentJson = dict[str, ArtifactDocumentJsonValue]


class ArtifactDocumentRecord(Base):
    """Immutable canonical document versions; new versions always insert a row."""

    __tablename__ = "artifact_documents"
    __table_args__ = (
        UniqueConstraint("run_id", "artifact_id", "version", name="uq_artifact_documents_version"),
        Index("ix_artifact_documents_run_artifact", "run_id", "artifact_id"),
        {"schema": "public"},
    )

    document_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    artifact_id: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    audience: Mapped[str] = mapped_column(String(16), nullable=False)
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    parent_document_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="SET NULL"), nullable=True,
    )
    source_document_id: Mapped[str | None] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="SET NULL"), nullable=True,
    )
    document_json: Mapped[ArtifactDocumentJson] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AnswerSetRecord(Base):
    """Teacher-only answer data linked to one immutable document version."""

    __tablename__ = "answer_sets"
    __table_args__ = (
        UniqueConstraint("source_document_id", "source_version", name="uq_answer_sets_document_version"),
        Index("ix_answer_sets_source_document", "source_document_id"),
        {"schema": "public"},
    )

    answer_set_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    source_document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    authority: Mapped[str] = mapped_column(String(32), nullable=False)
    answer_set_json: Mapped[ArtifactDocumentJson] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContentVariantRecord(Base):
    """A bounded semantic variant derived from a source document."""

    __tablename__ = "content_variants"
    __table_args__ = (
        UniqueConstraint("document_id", "variant_kind", name="uq_content_variants_document_kind"),
        Index("ix_content_variants_source_document", "source_document_id"),
        {"schema": "public"},
    )

    variant_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    source_document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    variant_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContentDependencyRecord(Base):
    """A dependency edge used to mark derived V2 content stale after semantic edits."""

    __tablename__ = "content_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "source_document_id", "dependency_kind", name="uq_content_dependencies_edge",
        ),
        Index("ix_content_dependencies_source_document", "source_document_id"),
        {"schema": "public"},
    )

    dependency_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    source_document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    dependency_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ContentApprovalRecord(Base):
    """Append-only approval decisions for one V2 document version."""

    __tablename__ = "content_approvals"
    __table_args__ = (
        Index("ix_content_approvals_document", "document_id"),
        {"schema": "public"},
    )

    approval_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    approved_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ArtifactDocumentSnapshotRecord(Base):
    """Pins a V2 document version to an immutable rendered snapshot."""

    __tablename__ = "artifact_document_snapshots"
    __table_args__ = (Index("ix_artifact_document_snapshots_snapshot", "snapshot_id"), {"schema": "public"})

    document_id: Mapped[str] = mapped_column(
        String(80), ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"), primary_key=True,
    )
    snapshot_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.artifact_snapshots.snapshot_id", ondelete="CASCADE"), primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
