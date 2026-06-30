"""Tests for outcome_store — per-teacher CRUD, cross-teacher isolation.

Real DB: postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class
All rows are cleaned up after each test.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.outcome import DeliveryRecord, StudentAttempt, StudentKCState
from services.gateway.models import Base, Run, RunStatus
from services.gateway.outcome_models import (
    DeliveryRecordModel,
    GuardianConsent,
    StudentAttemptRecord,
    StudentKCStateRecord,
)
from services.gateway.outcome_store import (
    get_kc_state,
    mastery_for,
    record_attempt,
    record_delivery,
    upsert_kc_state,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

_NOW = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_conn: set(Base.metadata.tables)
        )
        if "public.student_attempts" not in existing_tables:
            pytest.skip("student_attempts table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uid() -> str:
    return str(uuid4())


def _attempt(
    teacher_id: str,
    delivery_id: str,
    student_pseudonym: str = "sha256:student-a",
    kc_ids: list[str] | None = None,
) -> StudentAttempt:
    return StudentAttempt(
        attempt_id=_uid(),
        student_pseudonym=student_pseudonym,
        question_id="q-001",
        kc_ids=kc_ids or ["KC-fractions"],
        correct=True,
        score=1.0,
        timestamp=_NOW,
        delivery_id=delivery_id,
    )


def _kc_state(
    teacher_id: str,
    student_pseudonym: str = "sha256:student-a",
    kc_id: str = "KC-fractions",
    mastery: float = 0.6,
) -> StudentKCState:
    return StudentKCState(
        state_id=_uid(),
        student_pseudonym=student_pseudonym,
        kc_id=kc_id,
        mastery=mastery,
        params={"p_L0": 0.3},
        updated_at=_NOW,
    )


async def _create_run(session: AsyncSession, run_id: str, teacher_id: str) -> str:
    run = Run(
        run_id=run_id,
        teacher_id=teacher_id,
        status=RunStatus.COMPLETED,
        current_step=1,
        raw_request="test run for outcome store",
    )
    session.add(run)
    await session.flush()
    return run_id


# ---------------------------------------------------------------------------
# record_attempt
# ---------------------------------------------------------------------------


class TestRecordAttempt:
    async def test_records_and_reads_back_scoped_to_teacher(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        delivery_id = _uid()
        attempt = _attempt(teacher_id=teacher_id, delivery_id=delivery_id)

        await record_attempt(session, attempt, teacher_id)
        await session.commit()

        result = await session.execute(
            select(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id,
                StudentAttemptRecord.teacher_id == teacher_id,
            )
        )
        row = result.scalar_one()

        assert row.student_pseudonym == attempt.student_pseudonym
        assert row.question_id == attempt.question_id
        assert row.kc_ids == attempt.kc_ids
        assert row.correct is True
        assert row.score == 1.0
        assert row.delivery_id == delivery_id
        assert row.teacher_id == teacher_id

        # cleanup
        await session.execute(
            delete(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id
            )
        )
        await session.commit()

    async def test_cross_teacher_cannot_read_another_teachers_attempts(
        self, session: AsyncSession
    ) -> None:
        teacher_a = f"teacher-a-{_uid()}"
        teacher_b = f"teacher-b-{_uid()}"
        delivery_id = _uid()
        attempt = _attempt(teacher_id=teacher_a, delivery_id=delivery_id)

        await record_attempt(session, attempt, teacher_a)
        await session.commit()

        # teacher B queries — should find nothing
        result = await session.execute(
            select(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id,
                StudentAttemptRecord.teacher_id == teacher_b,
            )
        )
        assert result.scalar_one_or_none() is None

        # cleanup
        await session.execute(
            delete(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# upsert_kc_state / get_kc_state
# ---------------------------------------------------------------------------


class TestKCState:
    async def test_upsert_creates_and_updates_mastery(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        state = _kc_state(teacher_id=teacher_id, mastery=0.4)

        await upsert_kc_state(session, state, teacher_id)
        await session.commit()

        fetched = await get_kc_state(
            session, teacher_id, state.student_pseudonym, state.kc_id
        )
        assert fetched is not None
        assert fetched.mastery == pytest.approx(0.4)

        # Update mastery
        updated = StudentKCState(
            state_id=state.state_id,
            student_pseudonym=state.student_pseudonym,
            kc_id=state.kc_id,
            mastery=0.85,
            params={"p_L0": 0.15},
            updated_at=_NOW,
        )
        await upsert_kc_state(session, updated, teacher_id)
        await session.commit()

        fetched2 = await get_kc_state(
            session, teacher_id, state.student_pseudonym, state.kc_id
        )
        assert fetched2 is not None
        assert fetched2.mastery == pytest.approx(0.85)

        # cleanup
        await session.execute(
            delete(StudentKCStateRecord).where(
                StudentKCStateRecord.teacher_id == teacher_id,
                StudentKCStateRecord.student_pseudonym == state.student_pseudonym,
            )
        )
        await session.commit()

    async def test_get_kc_state_returns_none_when_not_found(self, session: AsyncSession) -> None:
        result = await get_kc_state(session, "no-teacher", "no-student", "no-kc")
        assert result is None


# ---------------------------------------------------------------------------
# mastery_for
# ---------------------------------------------------------------------------


class TestMasteryFor:
    async def test_returns_average_mastery_per_kc_for_consented_students(
        self, session: AsyncSession
    ) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym_a = f"sha256:stu-a-{_uid()}"
        pseudonym_b = f"sha256:stu-b-{_uid()}"
        kc = "KC-fractions"

        # Grant consent for both students
        for pseudonym in [pseudonym_a, pseudonym_b]:
            session.add(
                GuardianConsent(
                    consent_id=_uid(),
                    teacher_id=teacher_id,
                    class_id=class_id,
                    student_pseudonym=pseudonym,
                    granted_at=_NOW,
                )
            )

        # Insert KC states: mastery 0.6 and 0.8 → avg 0.7
        for pseudonym, mastery in [(pseudonym_a, 0.6), (pseudonym_b, 0.8)]:
            state = _kc_state(
                teacher_id=teacher_id,
                student_pseudonym=pseudonym,
                kc_id=kc,
                mastery=mastery,
            )
            await upsert_kc_state(session, state, teacher_id)

        await session.commit()

        result = await mastery_for(session, teacher_id, class_id, [kc])

        assert result[kc] == pytest.approx(0.7, abs=1e-9)

        # cleanup
        await session.execute(
            delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id)
        )
        await session.execute(
            delete(StudentKCStateRecord).where(StudentKCStateRecord.teacher_id == teacher_id)
        )
        await session.commit()

    async def test_returns_zero_for_kc_with_no_data(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        result = await mastery_for(session, teacher_id, "class-x", ["KC-missing"])
        assert result == {"KC-missing": 0.0}

    async def test_returns_empty_dict_for_empty_kc_ids(self, session: AsyncSession) -> None:
        result = await mastery_for(session, "any-teacher", "any-class", [])
        assert result == {}


# ---------------------------------------------------------------------------
# record_delivery
# ---------------------------------------------------------------------------


class TestRecordDelivery:
    async def test_records_delivery_with_run_fk(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        run_id = f"run-{_uid()}"
        delivery_id = _uid()

        await _create_run(session, run_id, teacher_id)

        record = DeliveryRecord(
            delivery_id=delivery_id,
            run_id=run_id,
            teacher_id=teacher_id,
            kc_ids=["KC-fractions"],
            delivered_at=_NOW,
            class_id="class-5A",
        )
        await record_delivery(session, record)
        await session.commit()

        result = await session.execute(
            select(DeliveryRecordModel).where(
                DeliveryRecordModel.delivery_id == delivery_id
            )
        )
        row = result.scalar_one()
        assert row.run_id == run_id
        assert row.teacher_id == teacher_id
        assert row.kc_ids == ["KC-fractions"]

        # cleanup (cascade will handle delivery_records when run is deleted)
        await session.execute(delete(Run).where(Run.run_id == run_id))
        await session.commit()
