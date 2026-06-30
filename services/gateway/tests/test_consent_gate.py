"""Tests for the guardian consent gate.

Real DB: postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.outcome import StudentAttempt
from services.gateway.models import Base
from services.gateway.outcome_models import GuardianConsent, StudentAttemptRecord
from services.gateway.outcome_store import (
    grant_consent,
    has_consent,
    record_attempt,
    revoke_consent,
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
        if "public.guardian_consents" not in existing_tables:
            pytest.skip("guardian_consents table not present — run alembic upgrade head")
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


def _attempt(teacher_id: str, delivery_id: str, pseudonym: str) -> StudentAttempt:
    return StudentAttempt(
        attempt_id=_uid(),
        student_pseudonym=pseudonym,
        question_id="q-consent-check",
        kc_ids=["KC-test"],
        correct=True,
        score=1.0,
        timestamp=_NOW,
        delivery_id=delivery_id,
    )


# ---------------------------------------------------------------------------
# Consent lifecycle
# ---------------------------------------------------------------------------


class TestConsentGate:
    async def test_has_consent_returns_false_before_grant(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"

        result = await has_consent(session, teacher_id, class_id, pseudonym)
        assert result is False

    async def test_has_consent_returns_true_after_grant(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"

        await grant_consent(session, teacher_id, class_id, pseudonym)
        await session.commit()

        result = await has_consent(session, teacher_id, class_id, pseudonym)
        assert result is True

        # cleanup
        await session.execute(
            delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id)
        )
        await session.commit()

    async def test_revoke_consent_makes_has_consent_return_false(
        self, session: AsyncSession
    ) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"

        await grant_consent(session, teacher_id, class_id, pseudonym)
        await session.commit()

        assert await has_consent(session, teacher_id, class_id, pseudonym) is True

        await revoke_consent(session, teacher_id, class_id, pseudonym)
        await session.commit()

        assert await has_consent(session, teacher_id, class_id, pseudonym) is False

        # cleanup
        await session.execute(
            delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id)
        )
        await session.commit()

    async def test_revoke_is_idempotent_when_no_active_consent(
        self, session: AsyncSession
    ) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"

        # No prior grant — revoke should not raise
        await revoke_consent(session, teacher_id, class_id, pseudonym)
        await session.commit()

        assert await has_consent(session, teacher_id, class_id, pseudonym) is False

    async def test_consent_is_scoped_per_class(self, session: AsyncSession) -> None:
        teacher_id = f"teacher-{_uid()}"
        class_a = f"class-a-{_uid()}"
        class_b = f"class-b-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"

        await grant_consent(session, teacher_id, class_a, pseudonym)
        await session.commit()

        assert await has_consent(session, teacher_id, class_a, pseudonym) is True
        assert await has_consent(session, teacher_id, class_b, pseudonym) is False

        # cleanup
        await session.execute(
            delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id)
        )
        await session.commit()

    async def test_capture_is_blocked_without_consent(self, session: AsyncSession) -> None:
        """Behavioral test: caller MUST check has_consent before record_attempt.

        This test verifies the expected call sequence — if consent is absent,
        the caller should not invoke record_attempt.  We validate that the
        attempt is NOT recorded when the guard is respected.
        """
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"
        delivery_id = _uid()

        # No consent granted
        consent_present = await has_consent(session, teacher_id, class_id, pseudonym)

        attempt = _attempt(teacher_id, delivery_id, pseudonym)

        if consent_present:
            await record_attempt(session, attempt, teacher_id)

        await session.commit()

        # attempt must NOT be in the DB
        from sqlalchemy import select
        result = await session.execute(
            select(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id
            )
        )
        assert result.scalar_one_or_none() is None

    async def test_capture_succeeds_after_consent_is_granted(self, session: AsyncSession) -> None:
        """Behavioral test: attempt IS recorded when consent is present."""
        teacher_id = f"teacher-{_uid()}"
        class_id = f"class-{_uid()}"
        pseudonym = f"sha256:student-{_uid()}"
        delivery_id = _uid()

        await grant_consent(session, teacher_id, class_id, pseudonym)
        await session.commit()

        consent_present = await has_consent(session, teacher_id, class_id, pseudonym)
        assert consent_present is True

        attempt = _attempt(teacher_id, delivery_id, pseudonym)

        if consent_present:
            await record_attempt(session, attempt, teacher_id)

        await session.commit()

        from sqlalchemy import select
        result = await session.execute(
            select(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id
            )
        )
        row = result.scalar_one()
        assert row.student_pseudonym == pseudonym

        # cleanup
        await session.execute(
            delete(StudentAttemptRecord).where(
                StudentAttemptRecord.attempt_id == attempt.attempt_id
            )
        )
        await session.execute(
            delete(GuardianConsent).where(GuardianConsent.teacher_id == teacher_id)
        )
        await session.commit()
