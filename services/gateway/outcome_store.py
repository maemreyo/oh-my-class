"""Outcome store — async CRUD for the effectiveness-loop subsystem.

Every query is scoped by teacher_id to enforce tenant isolation.
Guardian consent must be checked before recording any attempt.

Privacy (PDPD 13/2023): only pseudonym + KC-mastery + score are written;
raw student responses or real PII must never be passed into these functions.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.contracts.outcome import DeliveryRecord, StudentAttempt, StudentKCState
from services.gateway.outcome_models import (
    DeliveryRecordModel,
    GuardianConsent,
    StudentAttemptRecord,
    StudentKCStateRecord,
)


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


async def record_attempt(
    session: AsyncSession,
    attempt: StudentAttempt,
    teacher_id: str,
) -> None:
    """Persist a student attempt scoped to teacher_id."""
    row = StudentAttemptRecord(
        attempt_id=attempt.attempt_id,
        student_pseudonym=attempt.student_pseudonym,
        question_id=attempt.question_id,
        kc_ids=attempt.kc_ids,
        correct=attempt.correct,
        score=attempt.score,
        timestamp=attempt.timestamp,
        delivery_id=attempt.delivery_id,
        teacher_id=teacher_id,
    )
    session.add(row)
    await session.flush()


# ---------------------------------------------------------------------------
# KC state
# ---------------------------------------------------------------------------


async def get_kc_state(
    session: AsyncSession,
    teacher_id: str,
    student_pseudonym: str,
    kc_id: str,
) -> StudentKCState | None:
    """Return the current KC state for a student, or None if not found."""
    stmt = select(StudentKCStateRecord).where(
        StudentKCStateRecord.teacher_id == teacher_id,
        StudentKCStateRecord.student_pseudonym == student_pseudonym,
        StudentKCStateRecord.kc_id == kc_id,
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return StudentKCState(
        state_id=row.state_id,
        student_pseudonym=row.student_pseudonym,
        kc_id=row.kc_id,
        mastery=row.mastery,
        params=row.params,
        updated_at=row.updated_at,
    )


async def upsert_kc_state(
    session: AsyncSession,
    state: StudentKCState,
    teacher_id: str,
) -> None:
    """Insert or update KC mastery state (on unique teacher+pseudonym+kc)."""
    stmt = (
        pg_insert(StudentKCStateRecord)
        .values(
            state_id=state.state_id,
            student_pseudonym=state.student_pseudonym,
            kc_id=state.kc_id,
            mastery=state.mastery,
            params=state.params,
            updated_at=state.updated_at,
            teacher_id=teacher_id,
        )
        .on_conflict_do_update(
            constraint="uq_student_kc_states_teacher_pseudo_kc",
            set_={
                "mastery": state.mastery,
                "params": state.params,
                "updated_at": state.updated_at,
                "state_id": state.state_id,
            },
        )
    )
    await session.execute(stmt)
    await session.flush()


async def mastery_for(
    session: AsyncSession,
    teacher_id: str,
    class_id: str,
    kc_ids: list[str],
) -> dict[str, float]:
    """Return average mastery per KC across all students in a class.

    Students are identified by pseudonyms that appear in guardian_consents
    for this teacher+class combination.  Returns 0.0 for KCs with no data.
    """
    if not kc_ids:
        return {}

    # Pseudonyms that have active consent for this class
    consented_pseudonyms_stmt = select(GuardianConsent.student_pseudonym).where(
        GuardianConsent.teacher_id == teacher_id,
        GuardianConsent.class_id == class_id,
        GuardianConsent.revoked_at.is_(None),
    )

    stmt = (
        select(
            StudentKCStateRecord.kc_id,
            func.avg(StudentKCStateRecord.mastery).label("avg_mastery"),
        )
        .where(
            StudentKCStateRecord.teacher_id == teacher_id,
            StudentKCStateRecord.kc_id.in_(kc_ids),
            StudentKCStateRecord.student_pseudonym.in_(consented_pseudonyms_stmt),
        )
        .group_by(StudentKCStateRecord.kc_id)
    )
    result = await session.execute(stmt)
    rows = result.all()
    out: dict[str, float] = {kc_id: 0.0 for kc_id in kc_ids}
    for row in rows:
        out[row.kc_id] = float(row.avg_mastery)
    return out


# ---------------------------------------------------------------------------
# Delivery records
# ---------------------------------------------------------------------------


async def record_delivery(session: AsyncSession, record: DeliveryRecord) -> None:
    """Persist a delivery record (written post-export, non-blocking caller side)."""
    row = DeliveryRecordModel(
        delivery_id=record.delivery_id,
        run_id=record.run_id,
        teacher_id=record.teacher_id,
        kc_ids=record.kc_ids,
        delivered_at=record.delivered_at,
        class_id=record.class_id,
    )
    session.add(row)
    await session.flush()


# ---------------------------------------------------------------------------
# Guardian consent gate
# ---------------------------------------------------------------------------


async def has_consent(
    session: AsyncSession,
    teacher_id: str,
    class_id: str,
    student_pseudonym: str,
) -> bool:
    """Return True if an active (non-revoked) consent exists."""
    stmt = select(GuardianConsent.consent_id).where(
        GuardianConsent.teacher_id == teacher_id,
        GuardianConsent.class_id == class_id,
        GuardianConsent.student_pseudonym == student_pseudonym,
        GuardianConsent.revoked_at.is_(None),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def grant_consent(
    session: AsyncSession,
    teacher_id: str,
    class_id: str,
    student_pseudonym: str,
) -> None:
    """Record a new guardian consent grant."""
    row = GuardianConsent(
        consent_id=str(uuid4()),
        teacher_id=teacher_id,
        class_id=class_id,
        student_pseudonym=student_pseudonym,
        granted_at=datetime.now(UTC),
        revoked_at=None,
    )
    session.add(row)
    await session.flush()


async def revoke_consent(
    session: AsyncSession,
    teacher_id: str,
    class_id: str,
    student_pseudonym: str,
) -> None:
    """Mark the consent as revoked (sets revoked_at to now)."""
    stmt = select(GuardianConsent).where(
        GuardianConsent.teacher_id == teacher_id,
        GuardianConsent.class_id == class_id,
        GuardianConsent.student_pseudonym == student_pseudonym,
        GuardianConsent.revoked_at.is_(None),
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None:
        row.revoked_at = datetime.now(UTC)
        await session.flush()
