from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base
from services.gateway.teaching_session import service
from services.gateway.teaching_session.join import (
    JoinAccepted,
    JoinRateLimitState,
    JoinRejected,
    allow_join_attempt,
    find_joinable_session_by_room_code,
    generate_room_code,
    is_room_code_valid,
    join_session,
    room_code_join_payload,
)
from services.gateway.teaching_session.models import (
    ClassRosterEntry,
    RetentionTier,
    SessionStatus,
    TeachingSession,
)
from services.gateway.teaching_session.tokens import IdentityMode, SessionRole, verify_session_token

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
JWT_SECRET = "test-secret-minimum-32-characters"


def _session(**overrides: object) -> TeachingSession:
    defaults: dict[str, object] = {
        "session_id": "session-1",
        "teacher_id": "teacher-1",
        "deck_id": "deck-1",
        "snapshot_id": "snap-1",
        "retention_tier": RetentionTier.AGGREGATE,
        "status": SessionStatus.LIVE,
        "room_code": "654321",
    }
    defaults.update(overrides)
    return TeachingSession(**defaults)


class TestRoomCodeShape:
    def test_generate_room_code_is_six_numeric_digits(self) -> None:
        code = generate_room_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_join_payload_encodes_session_and_room_code(self) -> None:
        session = _session()
        payload = room_code_join_payload(session)
        assert session.session_id in payload
        assert session.room_code is not None
        assert session.room_code in payload


class TestRoomCodeLifetimeBound:
    """Amendment #3: room code validity is bounded to the session's lifetime."""

    @pytest.mark.parametrize("status", [SessionStatus.SCHEDULED, SessionStatus.LIVE])
    def test_valid_while_not_terminal(self, status: SessionStatus) -> None:
        assert is_room_code_valid(_session(status=status)) is True

    @pytest.mark.parametrize(
        "status", [SessionStatus.ENDED, SessionStatus.ARCHIVED, SessionStatus.EXPIRED],
    )
    def test_invalid_once_terminal(self, status: SessionStatus) -> None:
        assert is_room_code_valid(_session(status=status)) is False

    def test_invalid_without_a_room_code(self) -> None:
        assert is_room_code_valid(_session(room_code=None)) is False


def _allow(
    state: JoinRateLimitState, ip: str, code: str, now: datetime, limit: int, window: int,
) -> bool:
    return allow_join_attempt(
        state, client_ip=ip, room_code=code, now=now, limit=limit, window_seconds=window,
    )


class TestJoinRateLimiting:
    """Amendment #3: rate-limited by IP + room code, mirroring webhooks.py's sliding window."""

    def test_allows_up_to_the_limit_then_denies(self) -> None:
        state = JoinRateLimitState()
        now = datetime.now(UTC)
        for _ in range(3):
            assert _allow(state, "1.2.3.4", "111111", now, limit=3, window=60)
        assert not _allow(state, "1.2.3.4", "111111", now, limit=3, window=60)

    def test_different_room_codes_from_same_ip_are_independent(self) -> None:
        state = JoinRateLimitState()
        now = datetime.now(UTC)
        assert _allow(state, "1.2.3.4", "111111", now, limit=1, window=60)
        assert not _allow(state, "1.2.3.4", "111111", now, limit=1, window=60)
        assert _allow(state, "1.2.3.4", "222222", now, limit=1, window=60)

    def test_different_ips_for_same_room_code_are_independent(self) -> None:
        state = JoinRateLimitState()
        now = datetime.now(UTC)
        assert _allow(state, "1.1.1.1", "111111", now, limit=1, window=60)
        assert not _allow(state, "1.1.1.1", "111111", now, limit=1, window=60)
        assert _allow(state, "2.2.2.2", "111111", now, limit=1, window=60)

    def test_window_expiry_allows_a_retry(self) -> None:
        state = JoinRateLimitState()
        now = datetime.now(UTC)
        assert _allow(state, "1.2.3.4", "111111", now, limit=1, window=30)
        assert not _allow(state, "1.2.3.4", "111111", now, limit=1, window=30)
        later = now + timedelta(seconds=31)
        assert _allow(state, "1.2.3.4", "111111", later, limit=1, window=30)


class TestJoinSession:
    def test_anonymous_join_requires_no_email(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """base AC6 -- `join_session` has no email parameter at all."""
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session = _session()
        state = JoinRateLimitState()

        result = join_session(
            session, client_ip="1.2.3.4", room_code=session.room_code or "",
            now=datetime.now(UTC), rate_limit_state=state,
        )

        assert isinstance(result, JoinAccepted)
        assert result.role == SessionRole.STUDENT
        assert result.identity_mode == IdentityMode.ANONYMOUS
        claims = verify_session_token(result.token)
        assert claims.alias is None
        assert claims.roster_student_id is None

    def test_alias_join_is_pseudonymous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session = _session()
        result = join_session(
            session, client_ip="1.2.3.4", room_code=session.room_code or "",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(), alias="Table 3",
        )
        assert isinstance(result, JoinAccepted)
        assert result.identity_mode == IdentityMode.PSEUDONYMOUS

    def test_roster_join_is_roster_identity_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """base AC1: roster join is *authenticated* -- identity comes from a real roster row."""
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session = _session(retention_tier=RetentionTier.IDENTIFIABLE, class_id="class-5a")
        roster_entry = ClassRosterEntry(
            roster_entry_id="roster-1", class_id="class-5a", name="Alice",
            student_id="stu-42", imported_by="teacher-1",
        )

        result = join_session(
            session, client_ip="1.2.3.4", room_code=session.room_code or "",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(),
            roster_entry=roster_entry,
        )

        assert isinstance(result, JoinAccepted)
        assert result.identity_mode == IdentityMode.ROSTER
        claims = verify_session_token(result.token)
        assert claims.alias == "Alice"
        assert claims.roster_student_id == "stu-42"

    def test_roster_entry_from_a_different_class_is_rejected(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        session = _session(retention_tier=RetentionTier.IDENTIFIABLE, class_id="class-5a")
        other_class_entry = ClassRosterEntry(
            roster_entry_id="roster-1", class_id="class-6b", name="Alice",
            student_id="stu-42", imported_by="teacher-1",
        )

        result = join_session(
            session, client_ip="1.2.3.4", room_code=session.room_code or "",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(),
            roster_entry=other_class_entry,
        )

        assert result == JoinRejected(reason="roster_entry_not_in_class")

    def test_wrong_room_code_is_rejected(self) -> None:
        session = _session()
        result = join_session(
            session, client_ip="1.2.3.4", room_code="000000",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(),
        )
        assert result == JoinRejected(reason="invalid_room_code")

    def test_no_session_found_is_rejected(self) -> None:
        result = join_session(
            None, client_ip="1.2.3.4", room_code="123456",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(),
        )
        assert result == JoinRejected(reason="invalid_room_code")

    def test_ended_session_is_rejected(self) -> None:
        session = _session(status=SessionStatus.ENDED)
        result = join_session(
            session, client_ip="1.2.3.4", room_code=session.room_code or "",
            now=datetime.now(UTC), rate_limit_state=JoinRateLimitState(),
        )
        assert result == JoinRejected(reason="session_not_joinable")

    def test_rate_limited_before_room_code_is_even_checked(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("JWT_SECRET", JWT_SECRET)
        monkeypatch.setenv("TEACHING_SESSION_JOIN_RATE_LIMIT_COUNT", "1")
        session = _session()
        state = JoinRateLimitState()
        now = datetime.now(UTC)
        code = session.room_code or ""

        first = join_session(
            session, client_ip="1.2.3.4", room_code=code, now=now, rate_limit_state=state,
        )
        second = join_session(
            session, client_ip="1.2.3.4", room_code=code, now=now, rate_limit_state=state,
        )

        assert isinstance(first, JoinAccepted)
        assert second == JoinRejected(reason="rate_limited")


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


class TestRoomCodeAssignedAtCreation:
    async def test_create_session_assigns_a_six_digit_room_code(self, db: AsyncSession) -> None:
        created = await service.create_session(
            db, session_id=f"session-{uuid4()}", teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1", snapshot_id="snap-1",
        )
        await db.commit()

        assert created.room_code is not None
        assert len(created.room_code) == 6
        assert created.room_code.isdigit()

    async def test_room_code_is_findable_while_joinable(self, db: AsyncSession) -> None:
        created = await service.create_session(
            db, session_id=f"session-{uuid4()}", teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1", snapshot_id="snap-1",
        )
        await db.commit()
        assert created.room_code is not None

        found = await find_joinable_session_by_room_code(db, created.room_code)
        assert found is not None
        assert found.session_id == created.session_id

    async def test_room_code_not_findable_once_session_is_terminal(self, db: AsyncSession) -> None:
        created = await service.create_session(
            db, session_id=f"session-{uuid4()}", teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1", snapshot_id="snap-1",
        )
        assert created.room_code is not None
        created.status = SessionStatus.ENDED
        await db.flush()

        found = await find_joinable_session_by_room_code(db, created.room_code)
        assert found is None
