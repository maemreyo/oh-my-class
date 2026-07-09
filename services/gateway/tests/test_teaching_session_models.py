from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base
from services.gateway.teaching_session import service
from services.gateway.teaching_session.models import (
    RetentionTier,
    SessionAuditEvent,
    SessionStatus,
    TeachingSession,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


class TestRetentionTierImmutability:
    """AC: retention tier is chosen once at creation and cannot silently escalate."""

    def test_reassigning_a_different_tier_raises(self) -> None:
        session = TeachingSession(
            session_id="s1", teacher_id="t1", deck_id="d1", snapshot_id="snap1",
            retention_tier=RetentionTier.AGGREGATE,
        )

        with pytest.raises(ValueError, match="locked at session creation"):
            session.retention_tier = RetentionTier.IDENTIFIABLE

    def test_reassigning_the_same_tier_is_a_no_op(self) -> None:
        session = TeachingSession(
            session_id="s1", teacher_id="t1", deck_id="d1", snapshot_id="snap1",
            retention_tier=RetentionTier.PSEUDONYMOUS,
        )

        session.retention_tier = RetentionTier.PSEUDONYMOUS

        assert session.retention_tier == RetentionTier.PSEUDONYMOUS

    def test_default_status_is_scheduled(self) -> None:
        session = TeachingSession(
            session_id="s1", teacher_id="t1", deck_id="d1", snapshot_id="snap1",
            retention_tier=RetentionTier.AGGREGATE, status=SessionStatus.SCHEDULED,
        )
        assert session.status == SessionStatus.SCHEDULED


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.teaching_sessions" not in existing_tables:
            pytest.skip("teaching_sessions table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestCreateSessionService:
    async def test_creates_session_with_default_aggregate_tier(self, db: AsyncSession) -> None:
        """AC4: aggregate/minimal is the default K-12 policy, not identifiable."""
        session_id = f"session-{uuid4()}"

        created = await service.create_session(
            db,
            session_id=session_id,
            teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1",
            snapshot_id="snap-1",
        )
        await db.commit()

        assert created.retention_tier == RetentionTier.AGGREGATE
        assert created.status == SessionStatus.SCHEDULED

    async def test_rejects_pseudonymous_without_class_id(self, db: AsyncSession) -> None:
        with pytest.raises(OMCError) as excinfo:
            await service.create_session(
                db,
                session_id=f"session-{uuid4()}",
                teacher_id=f"teacher-{uuid4()}",
                deck_id="deck-1",
                snapshot_id="snap-1",
                retention_tier=RetentionTier.PSEUDONYMOUS,
                class_id=None,
            )
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR

    async def test_rejects_identifiable_without_acknowledgment(self, db: AsyncSession) -> None:
        with pytest.raises(OMCError) as excinfo:
            await service.create_session(
                db,
                session_id=f"session-{uuid4()}",
                teacher_id=f"teacher-{uuid4()}",
                deck_id="deck-1",
                snapshot_id="snap-1",
                retention_tier=RetentionTier.IDENTIFIABLE,
                class_id="class-5a",
                identifiable_acknowledged=False,
            )
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR

    async def test_identifiable_with_class_id_and_ack_persists_audit_event(
        self, db: AsyncSession,
    ) -> None:
        """AC: choosing identifiable requires an acknowledgment persisted to the audit trail."""
        session_id = f"session-{uuid4()}"
        teacher_id = f"teacher-{uuid4()}"

        created = await service.create_session(
            db,
            session_id=session_id,
            teacher_id=teacher_id,
            deck_id="deck-1",
            snapshot_id="snap-1",
            class_id="class-5a",
            retention_tier=RetentionTier.IDENTIFIABLE,
            identifiable_acknowledged=True,
        )
        await db.commit()

        assert created.retention_tier == RetentionTier.IDENTIFIABLE

        result = await db.execute(
            select(SessionAuditEvent).where(SessionAuditEvent.session_id == session_id),
        )
        audit_events = result.scalars().all()

        assert len(audit_events) == 1
        assert audit_events[0].actor_id == teacher_id
        assert audit_events[0].action == "retention_tier_identifiable_acknowledged"

    async def test_aggregate_tier_does_not_create_an_audit_event(self, db: AsyncSession) -> None:
        session_id = f"session-{uuid4()}"

        await service.create_session(
            db,
            session_id=session_id,
            teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1",
            snapshot_id="snap-1",
        )
        await db.commit()

        result = await db.execute(
            select(SessionAuditEvent).where(SessionAuditEvent.session_id == session_id),
        )
        assert result.scalars().all() == []
