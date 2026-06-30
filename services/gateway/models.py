"""SQLAlchemy models for oh-my-class app data.

Schema: public
Tables: users, runs, artifacts, cost_logs
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserRole(StrEnum):
    TEACHER = "teacher"
    ADMIN = "admin"


class RunStatus(StrEnum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    GENERATING = "generating"
    REVIEWING = "reviewing"
    AWAITING_APPROVAL = "awaiting_approval"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UnitRole(StrEnum):
    STANDALONE = "standalone"
    UNIT_PARENT = "unit_parent"
    UNIT_SESSION = "unit_session"


class User(Base):
    """Teacher or admin user."""
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.TEACHER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Run(Base):
    """A teaching pack generation run."""
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("parent_run_id", "session_id", name="uq_runs_parent_session"),
        Index("ix_runs_parent_run_id", "parent_run_id"),
        {"schema": "public"},
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, native_enum=False), nullable=False, default=RunStatus.PENDING,
    )
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    raw_request: Mapped[str] = mapped_column(Text, nullable=False)
    class_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    lesson_plan: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    artifact_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    theme: Mapped[str] = mapped_column(String(32), default="default")
    quality_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    quality_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    teacher_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    revision_count: Mapped[int] = mapped_column(Integer, default=0)
    revision_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    export_formats: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parent_run_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("public.runs.run_id", ondelete="CASCADE"), nullable=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    session_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_role: Mapped[UnitRole] = mapped_column(
        Enum(UnitRole, native_enum=False, values_callable=lambda enum: [role.value for role in enum]),
        nullable=False,
        default=UnitRole.STANDALONE,
    )
    lesson_sequence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    shared_research: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    persona_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ClassProfileModel(Base):
    __tablename__ = "class_profiles"
    __table_args__ = (
        Index("ix_class_profiles_teacher_id", "teacher_id"),
        {"schema": "public"},
    )

    class_profile_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


class DecompositionFeedbackModel(Base):
    __tablename__ = "decomposition_feedback"
    __table_args__ = (
        Index("ix_decomposition_feedback_teacher_id", "teacher_id"),
        {"schema": "public"},
    )

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    proposed_sequence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    approved_sequence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    edit_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DecompositionTemplateModel(Base):
    __tablename__ = "decomposition_templates"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id",
            "topic_normalized",
            "grade",
            "subject",
            "locale",
            name="uq_decomposition_template_key",
        ),
        {"schema": "public"},
    )

    template_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    topic_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    grade: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False)
    locale: Mapped[str] = mapped_column(String(16), nullable=False)
    approved_sequence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class TeacherPreferenceModel(Base):
    __tablename__ = "teacher_decomposition_preferences"
    __table_args__ = (
        UniqueConstraint("teacher_id", name="uq_teacher_decomposition_preferences_teacher"),
        {"schema": "public"},
    )

    teacher_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Artifact(Base):
    """A generated artifact (lesson, worksheet, quiz, etc.)."""
    __tablename__ = "artifacts"
    __table_args__ = {"schema": "public"}

    artifact_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    theme: Mapped[str] = mapped_column(String(32), default="default")
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rendered_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class CostLog(Base):
    """LLM cost tracking per call."""
    __tablename__ = "cost_logs"
    __table_args__ = {"schema": "litellm"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
