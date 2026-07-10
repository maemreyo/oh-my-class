"""Persistence for immutable Media Asset versions, their artifact dependents,
and teacher-handled Visual Source Suggestions (ADR-056)."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class MediaAssetVersionRecord(Base):
    """One immutable version of a media asset. Never updated in place --
    replacement inserts a new row with the same `asset_id` and `version + 1`."""

    __tablename__ = "media_asset_versions"
    __table_args__ = (
        Index("ix_media_asset_versions_asset", "asset_id"),
        {"schema": "public"},
    )

    version_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    asset_id: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_scope: Mapped[str] = mapped_column(String(24), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    license_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    parent_version_id: Mapped[str | None] = mapped_column(
        String(80),
        ForeignKey("public.media_asset_versions.version_id", ondelete="SET NULL"),
        nullable=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MediaAssetDependencyRecord(Base):
    """Records that one artifact document version references one media asset
    version -- the substrate for "replacement creates dependency impact"."""

    __tablename__ = "media_asset_dependencies"
    __table_args__ = (
        Index("ix_media_asset_dependencies_version", "media_version_id"),
        Index("ix_media_asset_dependencies_document", "document_id"),
        {"schema": "public"},
    )

    dependency_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    media_version_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("public.media_asset_versions.version_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("public.artifact_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VisualSourceSuggestionRecord(Base):
    """A teacher-reviewable candidate visual. Never itself an artifact asset --
    see `common/contracts/visual_source_suggestion.py`."""

    __tablename__ = "visual_source_suggestions"
    __table_args__ = (
        Index("ix_visual_source_suggestions_run", "run_id"),
        {"schema": "public"},
    )

    suggestion_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    description: Mapped[str] = mapped_column(String(1_000), nullable=False)
    candidate_url: Mapped[str | None] = mapped_column(String(2_000), nullable=True)
    license_hint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    converted_asset_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
