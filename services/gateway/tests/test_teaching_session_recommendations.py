from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from services.gateway.exceptions import ErrorCode, OMCError
from services.gateway.models import Base
from services.gateway.teaching_session import service
from services.gateway.teaching_session.models import DeliveryMode, RetentionTier, SessionAuditEvent
from services.gateway.teaching_session.recommendations import (
    RECOMMENDATION_ARTIFACT_TYPES,
    RecommendationKind,
    RecommendationStatus,
    approve_recommendation,
    create_pending_recommendation,
    generate_recommendation_candidates,
)
from services.gateway.teaching_session.responses import MisconceptionRollupRow

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


class TestGenerateRecommendationCandidates:
    """AC: recommendations cite aggregate/concept evidence, never raw student data."""

    def test_no_aggregates_produces_no_candidates(self) -> None:
        assert generate_recommendation_candidates([]) == []

    def test_weak_concept_produces_reteach_practice_and_homework(self) -> None:
        rollup = [MisconceptionRollupRow(key="kc-1", attempt_count=10, correct_count=2)]

        candidates = generate_recommendation_candidates(rollup)

        kinds = {c.kind for c in candidates}
        assert RecommendationKind.RETEACH_MINI_DECK in kinds
        assert RecommendationKind.PRACTICE_WORKSHEET in kinds
        assert RecommendationKind.HOMEWORK in kinds
        for candidate in candidates:
            assert candidate.evidence_keys  # cites concept keys, not student pseudonyms
            is_next_lesson = candidate.kind == RecommendationKind.NEXT_LESSON_ADJUSTMENT
            assert "kc-1" in candidate.evidence_keys or is_next_lesson

    def test_strong_concept_only_produces_next_lesson_adjustment(self) -> None:
        rollup = [MisconceptionRollupRow(key="kc-1", attempt_count=10, correct_count=9)]

        candidates = generate_recommendation_candidates(rollup)

        assert [c.kind for c in candidates] == [RecommendationKind.NEXT_LESSON_ADJUSTMENT]

    def test_every_recommendation_kind_maps_to_an_existing_artifact_type(self) -> None:
        assert set(RECOMMENDATION_ARTIFACT_TYPES) == set(RecommendationKind)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(
            lambda sync_connection: set(Base.metadata.tables),
        )
        if "public.session_recommendations" not in existing_tables:
            pytest.skip("session_recommendations table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


class TestApprovalGate:
    """AC: recommendations require teacher approval before generation."""

    async def test_new_recommendation_starts_pending(self, db: AsyncSession) -> None:
        from services.gateway.teaching_session.recommendations import RecommendationCandidate

        recommendation = await create_pending_recommendation(
            db,
            session_id=f"session-{uuid4()}",
            candidate=RecommendationCandidate(
                kind=RecommendationKind.PRACTICE_WORKSHEET,
                evidence_keys=["kc-1"],
                rationale="test",
            ),
        )

        assert recommendation.status == RecommendationStatus.PENDING.value

    async def test_approve_calls_generate_one_artifact_exactly_once(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from services.gateway.teaching_session.recommendations import RecommendationCandidate

        calls: list[dict[str, Any]] = []

        async def fake_generate_one_artifact(payload: dict[str, Any]) -> dict[str, Any]:
            calls.append(payload)
            return {"artifact_chunks": []}

        monkeypatch.setattr(
            "packages.agents.teaching_pack.generate_one_artifact.generate_one_artifact",
            fake_generate_one_artifact,
        )

        created = await service.create_session(
            db,
            session_id=f"session-{uuid4()}",
            teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1",
            snapshot_id="snap-1",
        )
        session_id = created.session_id
        recommendation = await create_pending_recommendation(
            db,
            session_id=session_id,
            candidate=RecommendationCandidate(
                kind=RecommendationKind.PRACTICE_WORKSHEET,
                evidence_keys=["kc-1"],
                rationale="test",
            ),
        )

        # Not yet approved: no generation call happened.
        assert calls == []

        await approve_recommendation(
            db,
            recommendation_id=recommendation.recommendation_id,
            approver_id="teacher-1",
            delivery_mode=DeliveryMode.LIVE,
            retention_tier=RetentionTier.AGGREGATE,
            generate_payload={"artifact_type": "worksheet"},
        )
        await db.commit()

        assert len(calls) == 1
        assert recommendation.status == RecommendationStatus.APPROVED.value
        assert recommendation.approved_by == "teacher-1"

    async def test_approve_rejects_artifact_type_mismatch(self, db: AsyncSession) -> None:
        from services.gateway.teaching_session.recommendations import RecommendationCandidate

        recommendation = await create_pending_recommendation(
            db,
            session_id=f"session-{uuid4()}",
            candidate=RecommendationCandidate(
                kind=RecommendationKind.PRACTICE_WORKSHEET,
                evidence_keys=["kc-1"],
                rationale="test",
            ),
        )

        with pytest.raises(OMCError) as excinfo:
            await approve_recommendation(
                db,
                recommendation_id=recommendation.recommendation_id,
                approver_id="teacher-1",
                delivery_mode=DeliveryMode.LIVE,
                retention_tier=RetentionTier.AGGREGATE,
                generate_payload={"artifact_type": "quiz"},
            )
        assert excinfo.value.error_code == ErrorCode.VALIDATION_ERROR

    async def test_approve_writes_evidence_with_delivery_and_retention_mode(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from services.gateway.teaching_session.recommendations import RecommendationCandidate

        monkeypatch.setattr(
            "packages.agents.teaching_pack.generate_one_artifact.generate_one_artifact",
            lambda payload: _immediate({"artifact_chunks": []}),
        )

        created = await service.create_session(
            db,
            session_id=f"session-{uuid4()}",
            teacher_id=f"teacher-{uuid4()}",
            deck_id="deck-1",
            snapshot_id="snap-1",
        )
        session_id = created.session_id
        recommendation = await create_pending_recommendation(
            db,
            session_id=session_id,
            candidate=RecommendationCandidate(
                kind=RecommendationKind.HOMEWORK,
                evidence_keys=["kc-2"],
                rationale="test",
            ),
        )

        await approve_recommendation(
            db,
            recommendation_id=recommendation.recommendation_id,
            approver_id="teacher-2",
            delivery_mode=DeliveryMode.LIVE,
            retention_tier=RetentionTier.PSEUDONYMOUS,
            generate_payload={"artifact_type": "drill"},
        )
        await db.commit()

        result = await db.execute(
            select(SessionAuditEvent).where(
                SessionAuditEvent.session_id == session_id,
                SessionAuditEvent.action == "recommendation_approved",
            ),
        )
        events = result.scalars().all()
        assert len(events) == 1
        metadata = events[0].event_metadata
        assert metadata["delivery_mode"] == "live"
        assert metadata["retention_tier"] == "pseudonymous"
        assert metadata["kind"] == "homework"
        assert metadata["recommendation_id"] == recommendation.recommendation_id


async def _immediate(value: dict[str, Any]) -> dict[str, Any]:
    return value
