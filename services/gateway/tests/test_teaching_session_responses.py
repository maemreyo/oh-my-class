from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.models import Base
from services.gateway.outcome_models import StudentAttemptRecord
from services.gateway.teaching_pack_snapshot_html import render_student_preview_html
from services.gateway.teaching_session.models import RetentionTier
from services.gateway.teaching_session.responses import (
    STRUCTURED_RESPONSE_KINDS,
    DrillDownAccepted,
    DrillDownRejected,
    FreeTextAccepted,
    FreeTextRejected,
    GamificationMode,
    MisconceptionRollupRow,
    ResponseAccepted,
    ResponseKind,
    ResponseRejected,
    SessionResponseAggregate,
    SessionStudentResponse,
    class_collective_points,
    class_concept_rollup,
    gamification_mode_from_preference,
    gate_free_text,
    get_session_aggregates,
    get_session_raw_responses,
    private_student_points,
    record_response,
    student_drill_down,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


# ---------------------------------------------------------------------------
# Structured-first defaults (base AC1)
# ---------------------------------------------------------------------------


class TestStructuredFirstDefaults:
    def test_structured_kinds_do_not_include_free_text(self) -> None:
        assert ResponseKind.FREE_TEXT not in STRUCTURED_RESPONSE_KINDS

    def test_structured_kinds_cover_selection_and_short_structured(self) -> None:
        assert {
            ResponseKind.MULTIPLE_CHOICE, ResponseKind.POLL_VOTE, ResponseKind.SHORT_STRUCTURED,
        } == STRUCTURED_RESPONSE_KINDS


# ---------------------------------------------------------------------------
# Free-text gating (base AC2)
# ---------------------------------------------------------------------------


class TestFreeTextGating:
    def test_blocked_when_interaction_does_not_allow_free_text(self) -> None:
        result = gate_free_text(
            "a normal answer",
            interaction_allows_free_text=False,
            session_allows_free_text=True,
        )
        assert result == FreeTextRejected(reason="interaction_does_not_allow_free_text")

    def test_blocked_when_session_policy_blocks_free_text(self) -> None:
        result = gate_free_text(
            "a normal answer",
            interaction_allows_free_text=True,
            session_allows_free_text=False,
        )
        assert result == FreeTextRejected(reason="session_policy_blocks_free_text")

    def test_blocked_when_pii_detected(self) -> None:
        result = gate_free_text(
            "email me at student@example.com",
            interaction_allows_free_text=True,
            session_allows_free_text=True,
        )
        assert result == FreeTextRejected(reason="pii_detected")

    def test_accepted_when_allowed_and_clean(self) -> None:
        result = gate_free_text(
            "photosynthesis converts light into chemical energy",
            interaction_allows_free_text=True,
            session_allows_free_text=True,
        )
        assert result == FreeTextAccepted()


# ---------------------------------------------------------------------------
# `record_response` -- DB, retention-tier-gated (base AC3, amendment #2)
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.session_student_responses" not in existing_tables:
            pytest.skip("session_student_responses table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


def _mc_payload(option_id: str = "opt-a") -> dict[str, object]:
    return {"selected_option_ids": [option_id]}


class TestRecordResponseMalformedPayload:
    async def test_multiple_choice_requires_selected_option_ids(self, db: AsyncSession) -> None:
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id="s1",
            interaction_id="i1",
            retention_tier=RetentionTier.AGGREGATE,
            kind=ResponseKind.MULTIPLE_CHOICE,
            payload={},
            student_pseudonym="pseudo-1",
        )
        assert result == ResponseRejected(reason="multiple_choice_requires_selected_option_ids")


class TestRecordResponseRetentionGating:
    async def test_none_tier_persists_nothing(self, db: AsyncSession) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.NONE,
            kind=ResponseKind.MULTIPLE_CHOICE,
            payload=_mc_payload(),
            student_pseudonym="pseudo-1",
            correct=True,
        )
        await db.commit()

        assert result == ResponseAccepted(
            kind=ResponseKind.MULTIPLE_CHOICE, raw_response_persisted=False,
        )
        assert await get_session_aggregates(db, session_id=session_id) == []
        assert await get_session_raw_responses(db, session_id=session_id) == []

    async def test_aggregate_tier_increments_aggregate_but_writes_no_raw_row(
        self, db: AsyncSession,
    ) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.AGGREGATE,
            kind=ResponseKind.MULTIPLE_CHOICE,
            payload=_mc_payload(),
            student_pseudonym="pseudo-1",
            kc_ids=["kc-fractions"],
            correct=True,
        )
        await db.commit()

        assert result == ResponseAccepted(
            kind=ResponseKind.MULTIPLE_CHOICE, raw_response_persisted=False,
        )
        aggregates = await get_session_aggregates(db, session_id=session_id)
        assert len(aggregates) == 1
        assert aggregates[0].attempt_count == 1
        assert aggregates[0].correct_count == 1
        assert await get_session_raw_responses(db, session_id=session_id) == []

    async def test_pseudonymous_tier_writes_both_aggregate_and_raw_row(
        self, db: AsyncSession,
    ) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.PSEUDONYMOUS,
            kind=ResponseKind.MULTIPLE_CHOICE,
            payload=_mc_payload(),
            student_pseudonym="pseudo-1",
            kc_ids=["kc-fractions"],
            correct=False,
        )
        await db.commit()

        assert result == ResponseAccepted(
            kind=ResponseKind.MULTIPLE_CHOICE, raw_response_persisted=True,
        )
        aggregates = await get_session_aggregates(db, session_id=session_id)
        assert aggregates[0].attempt_count == 1
        assert aggregates[0].correct_count == 0
        raw_responses = await get_session_raw_responses(db, session_id=session_id)
        assert len(raw_responses) == 1
        assert raw_responses[0].student_pseudonym == "pseudo-1"
        assert raw_responses[0].kc_ids == ["kc-fractions"]

    async def test_identifiable_tier_also_writes_both(self, db: AsyncSession) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.IDENTIFIABLE,
            kind=ResponseKind.POLL_VOTE,
            payload={"selected_option_id": "opt-a"},
            student_pseudonym="roster-42",
        )
        await db.commit()

        assert result.raw_response_persisted is True
        raw_responses = await get_session_raw_responses(db, session_id=session_id)
        assert len(raw_responses) == 1

    async def test_repeated_responses_to_same_interaction_accumulate_one_aggregate_row(
        self, db: AsyncSession,
    ) -> None:
        session_id = f"session-{uuid4()}"
        for correct in (True, False, True):
            await record_response(
                db,
                response_id=f"resp-{uuid4()}",
                session_id=session_id,
                interaction_id="i1",
                retention_tier=RetentionTier.AGGREGATE,
                kind=ResponseKind.MULTIPLE_CHOICE,
                payload=_mc_payload(),
                student_pseudonym="pseudo-1",
                correct=correct,
            )
        await db.commit()

        aggregates = await get_session_aggregates(db, session_id=session_id)
        assert len(aggregates) == 1
        assert aggregates[0].attempt_count == 3
        assert aggregates[0].correct_count == 2

    async def test_free_text_blocked_by_pii_persists_nothing(self, db: AsyncSession) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.IDENTIFIABLE,
            kind=ResponseKind.FREE_TEXT,
            payload={"text": "reach me at kid@example.com"},
            student_pseudonym="pseudo-1",
            interaction_allows_free_text=True,
            session_allows_free_text=True,
        )
        await db.commit()

        assert result == ResponseRejected(reason="pii_detected")
        assert await get_session_aggregates(db, session_id=session_id) == []
        assert await get_session_raw_responses(db, session_id=session_id) == []

    async def test_free_text_accepted_when_clean_and_allowed(self, db: AsyncSession) -> None:
        session_id = f"session-{uuid4()}"
        result = await record_response(
            db,
            response_id=f"resp-{uuid4()}",
            session_id=session_id,
            interaction_id="i1",
            retention_tier=RetentionTier.PSEUDONYMOUS,
            kind=ResponseKind.FREE_TEXT,
            payload={"text": "the mitochondria is the powerhouse of the cell"},
            student_pseudonym="pseudo-1",
            interaction_allows_free_text=True,
            session_allows_free_text=True,
        )
        await db.commit()

        assert result.raw_response_persisted is True


# ---------------------------------------------------------------------------
# Default analytics: class-concept/misconception rollup (base AC4)
# ---------------------------------------------------------------------------


def _aggregate(
    *, interaction_id: str, kc_ids: list[str], attempts: int, correct: int,
) -> SessionResponseAggregate:
    return SessionResponseAggregate(
        aggregate_id=f"agg-{uuid4()}",
        session_id="s1",
        interaction_id=interaction_id,
        kc_ids=kc_ids,
        attempt_count=attempts,
        correct_count=correct,
    )


class TestClassConceptRollup:
    def test_groups_by_kc_id_across_interactions(self) -> None:
        aggregates = [
            _aggregate(interaction_id="i1", kc_ids=["kc-fractions"], attempts=10, correct=6),
            _aggregate(interaction_id="i2", kc_ids=["kc-fractions"], attempts=5, correct=1),
        ]
        rows = class_concept_rollup(aggregates)
        assert len(rows) == 1
        assert rows[0].key == "kc-fractions"
        assert rows[0].attempt_count == 15
        assert rows[0].correct_count == 7
        assert rows[0].incorrect_count == 8

    def test_falls_back_to_interaction_when_no_kc_ids(self) -> None:
        aggregates = [_aggregate(interaction_id="i1", kc_ids=[], attempts=4, correct=4)]
        rows = class_concept_rollup(aggregates)
        assert rows == [
            MisconceptionRollupRow(key="interaction:i1", attempt_count=4, correct_count=4),
        ]

    def test_rollup_is_class_level_never_per_student(self) -> None:
        """The rollup type has no student field at all -- there is nothing to leak."""
        aggregates = [_aggregate(interaction_id="i1", kc_ids=["kc-x"], attempts=1, correct=1)]
        row = class_concept_rollup(aggregates)[0]
        assert not hasattr(row, "student_pseudonym")


# ---------------------------------------------------------------------------
# Gated drill-down (base AC5)
# ---------------------------------------------------------------------------


def _raw_response(*, student_pseudonym: str, correct: bool) -> SessionStudentResponse:
    return SessionStudentResponse(
        response_id=f"resp-{uuid4()}",
        session_id="s1",
        interaction_id="i1",
        student_pseudonym=student_pseudonym,
        kind=ResponseKind.MULTIPLE_CHOICE.value,
        kc_ids=["kc-x"],
        payload={"selected_option_ids": ["opt-a"]},
        correct=correct,
    )


class TestStudentDrillDown:
    @pytest.mark.parametrize("tier", [RetentionTier.NONE, RetentionTier.AGGREGATE])
    def test_rejected_below_pseudonymous(self, tier: RetentionTier) -> None:
        result = student_drill_down([], retention_tier=tier)
        assert result == DrillDownRejected(reason="retention_tier_does_not_allow_drill_down")

    @pytest.mark.parametrize("tier", [RetentionTier.PSEUDONYMOUS, RetentionTier.IDENTIFIABLE])
    def test_accepted_at_pseudonymous_or_identifiable(self, tier: RetentionTier) -> None:
        responses = [_raw_response(student_pseudonym="pseudo-1", correct=True)]
        result = student_drill_down(responses, retention_tier=tier)
        assert isinstance(result, DrillDownAccepted)
        assert result.rows[0].student_pseudonym == "pseudo-1"


# ---------------------------------------------------------------------------
# Gamification -- non-competitive (amendment #1)
# ---------------------------------------------------------------------------


class TestGamificationMode:
    def test_disabled_by_default(self) -> None:
        assert gamification_mode_from_preference(None) is GamificationMode.DISABLED

    def test_disabled_when_not_enabled(self) -> None:
        assert gamification_mode_from_preference({"enabled": False, "mode": "class_collective"}) \
            is GamificationMode.DISABLED

    def test_reads_private_per_student(self) -> None:
        pref = {"enabled": True, "mode": "private_per_student"}
        assert gamification_mode_from_preference(pref) is GamificationMode.PRIVATE_PER_STUDENT

    def test_unknown_mode_fails_closed_to_disabled(self) -> None:
        pref = {"enabled": True, "mode": "public_leaderboard"}
        assert gamification_mode_from_preference(pref) is GamificationMode.DISABLED

    def test_no_leaderboard_mode_exists(self) -> None:
        assert {m.value for m in GamificationMode} == {
            "disabled", "private_per_student", "class_collective",
        }


class TestGamificationPoints:
    def test_private_points_scoped_to_one_student_only(self) -> None:
        responses = [
            _raw_response(student_pseudonym="pseudo-1", correct=True),
            _raw_response(student_pseudonym="pseudo-1", correct=True),
            _raw_response(student_pseudonym="pseudo-2", correct=True),
        ]
        assert private_student_points(responses, student_pseudonym="pseudo-1") == 2

    def test_class_collective_points_is_a_single_number(self) -> None:
        aggregates = [
            _aggregate(interaction_id="i1", kc_ids=[], attempts=10, correct=6),
            _aggregate(interaction_id="i2", kc_ids=[], attempts=5, correct=3),
        ]
        assert class_collective_points(aggregates) == 9


# ---------------------------------------------------------------------------
# kc_ids tagging alignment with effectiveness-loop/el-001
# ---------------------------------------------------------------------------


class TestKcIdsAlignmentWithOutcomeStore:
    def test_kc_ids_column_shape_matches_student_attempt_record(self) -> None:
        """Same field name and JSON-list-of-str shape as
        `StudentAttemptRecord.kc_ids` (services/gateway/outcome_models.py,
        effectiveness-loop/el-001) -- so a future adapter reads this table
        without a reshape."""
        response_column = SessionStudentResponse.__table__.columns["kc_ids"]
        attempt_column = StudentAttemptRecord.__table__.columns["kc_ids"]
        assert type(response_column.type) is type(attempt_column.type)
        assert response_column.nullable is False
        assert attempt_column.nullable is False


# ---------------------------------------------------------------------------
# Standalone/local-only exports never call a response API (base AC7)
# ---------------------------------------------------------------------------


class TestStandaloneExportHasNoResponseApiCall:
    def test_student_preview_html_has_no_script_tags_or_api_paths(self) -> None:
        html = render_student_preview_html({
            "title": "Fractions",
            "sections": [{"body": "1/2 + 1/2 = 1"}],
        })
        lowered = html.lower()
        assert "<script" not in lowered
        assert "fetch(" not in lowered
        assert "/responses" not in lowered
        assert "teaching-session" not in lowered
