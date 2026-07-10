"""Persistence models for scoped Source Collections (ADR-051, ADR-054)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class SourceCollectionRecord(Base):
    """A scoped, owner-bound bundle of Source Collection entries."""

    __tablename__ = "source_collections"
    __table_args__ = ({"schema": "public"},)

    collection_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    scope: Mapped[str] = mapped_column(String(24), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SourceCollectionEntryRecord(Base):
    """One entry within a Source Collection."""

    __tablename__ = "source_collection_entries"
    __table_args__ = (
        Index("ix_source_collection_entries_collection", "collection_id"),
        {"schema": "public"},
    )

    entry_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    collection_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("public.source_collections.collection_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authority: Mapped[str] = mapped_column(String(16), nullable=False)
    url: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(String(8_000), nullable=True)
    subject_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    claim_value: Mapped[str | None] = mapped_column(String(500), nullable=True)
    copyright_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ClaimEvidenceRecord(Base):
    """A claim-to-evidence mapping for one V2 artifact-document version (ADR-055)."""

    __tablename__ = "claim_evidence"
    __table_args__ = (
        Index("ix_claim_evidence_document", "document_id"),
        {"schema": "public"},
    )

    claim_evidence_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_id: Mapped[str] = mapped_column(String(80), nullable=False)
    claim_text: Mapped[str] = mapped_column(String(2_000), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False)
    citation_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
