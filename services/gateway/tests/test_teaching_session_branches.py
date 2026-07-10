from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from packages.agents.slide_deck_engine.models import SlideDeckValidationReport
from services.gateway.models import Base
from services.gateway.teaching_session import branches
from services.gateway.teaching_session.branches import (
    BranchContentType,
    BranchRejected,
    BranchSource,
    PrecomputedBranch,
    create_precomputed_branch,
    list_precomputed_branches,
    validate_branch_quality,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    database_engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with database_engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda c: set(Base.metadata.tables))
        if "public.precomputed_branches" not in existing_tables:
            pytest.skip("precomputed_branches table is not present — run alembic upgrade head")
    yield database_engine
    await database_engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()


# ---------------------------------------------------------------------------
# Quality gate: the SAME gate real slide content passes (TSP-06 base AC2)
# ---------------------------------------------------------------------------


class TestValidateBranchQuality:
    def test_ordinary_branch_body_passes_registry_density_and_teacher_only_gates(self) -> None:
        reports = validate_branch_quality(
            "A gentler restatement of the idea for a struggling student.",
        )
        assert all(report.passed for report in reports)
        codes = {report.code for report in reports}
        # Reuses the real functions verbatim -- their exact passing codes show up.
        assert "registry_membership_ok" in codes
        assert "density_budget_ok" in codes
        assert "teacher_only_separation_ok" in codes


# ---------------------------------------------------------------------------
# Storage: create is the ONLY insert path, and it is fail-closed
# ---------------------------------------------------------------------------


class TestCreatePrecomputedBranch:
    async def test_persists_a_row_when_the_quality_gate_passes(self, db: AsyncSession) -> None:
        result = await create_precomputed_branch(
            db,
            deck_id="deck-1",
            slide_id="slide-1",
            branch_type=BranchContentType.HINT,
            label="Give a hint",
            body="Think about what happens when you split the whole into equal parts.",
            created_by="teacher-1",
        )
        assert isinstance(result, PrecomputedBranch)
        assert result.source == BranchSource.PRECOMPUTED.value

        fetched = await db.get(PrecomputedBranch, result.branch_id)
        assert fetched is not None
        assert fetched.deck_id == "deck-1"
        assert fetched.slide_id == "slide-1"

    async def test_rejects_and_persists_nothing_when_the_quality_gate_fails(
        self, db: AsyncSession, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Fail-closed proof: force a failing report (the real gate always
        passes for this v1's fixed single-block/no-interaction fragment
        shape -- see `validate_branch_quality`'s docstring -- so this
        monkeypatch exercises the *wiring* that must hold the moment a
        richer branch shape makes a real failure possible)."""
        failing_report = SlideDeckValidationReport(
            phase="engine_quality", passed=False, code="invalid_block",
            message="forced failure for the fail-closed test", scope="block",
        )
        monkeypatch.setattr(
            branches, "validate_branch_quality", lambda body: [failing_report],  # noqa: ARG005
        )

        deck_id = f"deck-{uuid4()}"
        result = await create_precomputed_branch(
            db,
            deck_id=deck_id,
            slide_id="slide-1",
            branch_type=BranchContentType.RETEACH,
            label="Reteach",
            body="anything",
            created_by="teacher-1",
        )

        assert isinstance(result, BranchRejected)
        assert result.reason == "quality_gate_failed"
        assert result.reports == [failing_report]

        rows = await db.execute(
            select(PrecomputedBranch).where(PrecomputedBranch.deck_id == deck_id),
        )
        assert rows.scalars().all() == []  # nothing was persisted


class TestListPrecomputedBranches:
    async def test_lists_only_the_matching_deck_and_slide(self, db: AsyncSession) -> None:
        deck_id = f"deck-{uuid4()}"
        await create_precomputed_branch(
            db, deck_id=deck_id, slide_id="slide-1", branch_type=BranchContentType.HINT,
            label="Hint", body="A hint body long enough to be meaningful.", created_by="teacher-1",
        )
        await create_precomputed_branch(
            db, deck_id=deck_id, slide_id="slide-2", branch_type=BranchContentType.CHALLENGE,
            label="Challenge", body="A challenge body long enough to be meaningful.",
            created_by="teacher-1",
        )

        matches = await list_precomputed_branches(db, deck_id=deck_id, slide_id="slide-1")

        assert [branch.label for branch in matches] == ["Hint"]
