"""SQLAlchemy models for the outcome store (effectiveness-loop subsystem).

Schema: public
Tables: student_attempts, student_kc_states, delivery_records, guardian_consents

Privacy (PDPD 13/2023): only pseudonym + KC-mastery + score stored.
Raw student PII must never appear in these tables.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, utc_now


class StudentAttemptRecord(Base):
    """One question attempt by a pseudonymised student."""

    __tablename__ = "student_attempts"
    __table_args__ = (
        Index("ix_student_attempts_teacher_pseudonym", "teacher_id", "student_pseudonym"),
        {"schema": "public"},
    )

    attempt_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_pseudonym: Mapped[str] = mapped_column(String(128), nullable=False)
    question_id: Mapped[str] = mapped_column(String(128), nullable=False)
    kc_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_id: Mapped[str] = mapped_column(String(64), nullable=False)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)


class StudentKCStateRecord(Base):
    """Per-student, per-KC mastery state (BKT or equivalent)."""

    __tablename__ = "student_kc_states"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "student_pseudonym", "kc_id",
            name="uq_student_kc_states_teacher_pseudo_kc",
        ),
        {"schema": "public"},
    )

    state_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_pseudonym: Mapped[str] = mapped_column(String(128), nullable=False)
    kc_id: Mapped[str] = mapped_column(String(64), nullable=False)
    mastery: Mapped[float] = mapped_column(Float, nullable=False)
    params: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)


class DeliveryRecordModel(Base):
    """Record of a teaching pack delivery (written post-export)."""

    __tablename__ = "delivery_records"
    __table_args__ = {"schema": "public"}

    delivery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("public.runs.run_id", ondelete="CASCADE"),
        nullable=False,
    )
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    kc_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    class_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class GuardianConsent(Base):
    """Guardian consent gate — capture is blocked until consent is granted."""

    __tablename__ = "guardian_consents"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "class_id", "student_pseudonym",
            name="uq_guardian_consents_active",
        ),
        {"schema": "public"},
    )

    consent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), nullable=False)
    class_id: Mapped[str] = mapped_column(String(64), nullable=False)
    student_pseudonym: Mapped[str] = mapped_column(String(128), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
