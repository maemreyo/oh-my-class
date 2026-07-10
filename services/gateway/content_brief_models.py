"""Persistence models for Content Briefs and their append-only strategy review path."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class ContentBriefRecord(Base):
    """The typed Content Brief handed to one specialist slot. Immutable once created --
    a plan change creates a new brief plus a `strategy_change_requests` row, never an
    in-place edit."""

    __tablename__ = "content_briefs"
    __table_args__ = (
        Index("ix_content_briefs_run", "run_id"),
        {"schema": "public"},
    )

    content_brief_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=False,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    brief_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StrategyReviewRecord(Base):
    """An append-only fill-failure or strategy-change entry against one Content Brief."""

    __tablename__ = "strategy_review_requests"
    __table_args__ = (
        Index("ix_strategy_review_requests_brief", "content_brief_id"),
        {"schema": "public"},
    )

    request_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    content_brief_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("public.content_briefs.content_brief_id", ondelete="CASCADE"),
        nullable=False,
    )
    request_type: Mapped[str] = mapped_column(String(24), nullable=False)
    reason_or_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str] = mapped_column(String(2_000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
