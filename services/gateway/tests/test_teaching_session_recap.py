from __future__ import annotations

import hashlib
import inspect
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base
from services.gateway.teaching_session import recap, service
from services.gateway.teaching_session.models import RetentionTier, SessionAuditEvent
from services.gateway.teaching_session.recap import (
    RecapRejected,
    RecapStatus,
    build_recap_text,
    generate_class_recap,
    get_shared_recap,
    share_class_recap,
    update_class_recap_draft,
)
from services.gateway.teaching_session.responses import MisconceptionRollupRow, record_response, ResponseKind

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


# ---------------------------------------------------------------------------
# Structural guard: this module can never reach the raw per-student table.
# ---------------------------------------------------------------------------


class TestStructuralAggregateOnlyGuard:
    """AC: recap content is generated only from aggregate data, never raw responses.

    This is checked structurally, not just behaviorally -- the recap module's
    own source must never name the raw-access functions/table, so the
    guarantee holds even for a future call path nobody wrote a runtime test
    for.
    """

    def test_recap_module_never_references_raw_response_access(self) -> None:
        # Only the *code* (functions/classes), not the module docstring's
        # prose explaining this very guarantee, needs to avoid these names.
        code_source = "\n".join(
            inspect.getsource(member)
            for _, member in inspect.getmembers(recap, predicate=inspect.isfunction)
        ) + "\n".join(
            inspect.getsource(member)
            for _, member in inspect.getmembers(recap, predicate=inspect.isclass)
            if member.__module__ == recap.__name__
        )
        for forbidden in ("student_drill_down", "get_session_raw_responses", "SessionStudentResponse"):
            assert forbidden not in code_source, f"recap.py code must never reference {forbidden}"

    def test_recap_module_only_imports_rollup_and_aggregates_from_responses(self) -> None:
        imported = {
            name for name, value in vars(recap).items()
            if getattr(value, "__module__", None) == "services.gateway.teaching_session.responses"
        }
        assert imported == {"MisconceptionRollupRow", "class_concept_rollup", "get_session_aggregates"}


# ---------------------------------------------------------------------------
# Templated recap text (pure)
# ---------------------------------------------------------------------------


class TestBuildRecapText:
    def test_empty_rollup_produces_generic_no_data_message(self) -> None:
        text = build_recap_text([])
        assert "Lớp mình" in text
        assert "chưa có dữ liệu" in text

    def test_never_contains_a_student_identifier_field(self) -> None:
        rollup = [
            MisconceptionRollupRow(key="kc-fractions", attempt_count=10, correct_count=9),
            MisconceptionRollupRow(key="kc-decimals", attempt_count=10, correct_count=2),
        ]
        text = build_recap_text(rollup)
        # MisconceptionRollupRow structurally has no student field to begin
        # with, but assert on the rendered text too for the concrete case.
        assert "student" not in text.lower()
        assert "pseudo" not in text.lower()
        assert "kc-fractions" in text
        assert "kc-decimals" in text


# ---------------------------------------------------------------------------
# DB-backed: generation gate, draft/edit/share flow, event logging
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.session_class_recaps" not in existing_tables:
            pytest.skip("session_class_recaps table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


async def _create_session(db: AsyncSession, *, retention_tier: RetentionTier) -> str:
    session_id = f"session-{uuid4()}"
    await service.create_session(
        db,
        session_id=session_id,
        teacher_id=f"teacher-{uuid4()}",
        deck_id="deck-1",
        snapshot_id="snap-1",
        class_id="class-1" if retention_tier is not RetentionTier.AGGREGATE else None,
        retention_tier=retention_tier,
        identifiable_acknowledged=retention_tier is RetentionTier.IDENTIFIABLE,
    )
    await db.commit()
    return session_id


class TestGenerationGate:
    """AC: recap content only ever comes from aggregate-or-coarser retention tiers."""

    async def test_session_not_found_is_rejected(self, db: AsyncSession) -> None:
        result = await generate_class_recap(db, session_id="does-not-exist", teacher_id="t1")
        assert result == RecapRejected(reason="session_not_found")

    async def test_aggregate_tier_generates_a_draft(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.AGGREGATE,
            kind=ResponseKind.MULTIPLE_CHOICE,
            payload={"selected_option_ids": ["a"]},
            student_pseudonym="anon-1",
            kc_ids=["kc-fractions"],
            correct=True,
        )
        await db.commit()

        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")

        assert not isinstance(draft, RecapRejected)
        assert draft.status == RecapStatus.DRAFT.value
        assert "kc-fractions" in draft.text

    async def test_none_tier_generates_a_generic_draft_with_no_data(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.NONE)

        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")

        assert not isinstance(draft, RecapRejected)
        assert "chưa có dữ liệu" in draft.text

    async def test_pseudonymous_tier_is_rejected(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.PSEUDONYMOUS)

        result = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")

        assert result == RecapRejected(reason="retention_tier_too_identifying")

    async def test_identifiable_tier_with_real_raw_rows_is_rejected_and_never_reads_them(
        self, db: AsyncSession,
    ) -> None:
        """The critical guard: real per-student rows exist, but the recap
        function refuses tier-wise before ever touching that table, and
        (per the structural test above) has no code path that even could."""
        session_id = await _create_session(db, retention_tier=RetentionTier.IDENTIFIABLE)
        await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.IDENTIFIABLE,
            kind=ResponseKind.POLL_VOTE,
            payload={"selected_option_id": "opt-a"},
            student_pseudonym="real-student-name-42",
            kc_ids=["kc-fractions"],
            correct=True,
        )
        await db.commit()

        result = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")

        assert result == RecapRejected(reason="retention_tier_too_identifying")


class TestDraftEditAndShare:
    """AC: teacher reviews/edits before sharing; sharing needs no new auth."""

    async def test_teacher_can_edit_draft_before_sharing(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")
        await db.commit()
        assert not isinstance(draft, RecapRejected)

        edited = await update_class_recap_draft(
            db, recap_id=draft.recap_id, text="Lớp mình học rất tốt hôm nay!",
        )
        await db.commit()

        assert edited.text == "Lớp mình học rất tốt hôm nay!"
        assert edited.status == RecapStatus.DRAFT.value

    async def test_share_mints_an_opaque_token_resolvable_without_auth(
        self, db: AsyncSession,
    ) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")
        await db.commit()
        assert not isinstance(draft, RecapRejected)

        shared = await share_class_recap(db, recap_id=draft.recap_id, teacher_id="teacher-1")
        await db.commit()

        assert shared.status == RecapStatus.SHARED.value
        assert shared.share_token

        looked_up = await get_shared_recap(db, share_token=shared.share_token)
        assert looked_up is not None
        assert looked_up.recap_id == draft.recap_id
        assert looked_up.text == shared.text

    async def test_unknown_share_token_resolves_to_none(self, db: AsyncSession) -> None:
        assert await get_shared_recap(db, share_token="not-a-real-token") is None

    async def test_editing_after_share_is_rejected(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")
        await db.commit()
        assert not isinstance(draft, RecapRejected)
        await share_class_recap(db, recap_id=draft.recap_id, teacher_id="teacher-1")
        await db.commit()

        with pytest.raises(OMCError) as excinfo:
            await update_class_recap_draft(db, recap_id=draft.recap_id, text="too late")
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR

    async def test_sharing_twice_is_rejected(self, db: AsyncSession) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")
        await db.commit()
        assert not isinstance(draft, RecapRejected)
        await share_class_recap(db, recap_id=draft.recap_id, teacher_id="teacher-1")
        await db.commit()

        with pytest.raises(OMCError) as excinfo:
            await share_class_recap(db, recap_id=draft.recap_id, teacher_id="teacher-1")
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR


class TestAuditEventWithoutContentDuplication:
    """AC: recap sharing is logged as a session event, without storing the
    shared content as new PII-bearing state."""

    async def test_share_logs_one_audit_event_with_a_hash_not_the_text(
        self, db: AsyncSession,
    ) -> None:
        session_id = await _create_session(db, retention_tier=RetentionTier.AGGREGATE)
        draft = await generate_class_recap(db, session_id=session_id, teacher_id="teacher-1")
        await db.commit()
        assert not isinstance(draft, RecapRejected)

        shared = await share_class_recap(db, recap_id=draft.recap_id, teacher_id="teacher-9")
        await db.commit()

        result = await db.execute(
            select(SessionAuditEvent).where(
                SessionAuditEvent.session_id == session_id,
                SessionAuditEvent.action == "class_recap_shared",
            ),
        )
        events = result.scalars().all()
        assert len(events) == 1
        metadata = events[0].event_metadata
        assert metadata["recap_id"] == draft.recap_id
        assert metadata["text_sha256"] == hashlib.sha256(shared.text.encode("utf-8")).hexdigest()
        assert "text" not in metadata
        assert shared.text not in str(metadata)
        assert events[0].actor_id == "teacher-9"
