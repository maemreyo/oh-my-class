"""TSP-06 live-router proof: precomputed branch listing + the on-the-fly AI
branch suggestion/apply pair, through the real, registered FastAPI routes --
same shape `test_teaching_session_live_router.py` uses for TSP-03's routes.

Two-layer no-raw-leakage guard (mirrors TSP-09's aggregate-only guard):
- Structural: `suggest_branch_content`'s own source never names
  `record_event`/`live_sync`/`publish_event` -- an AI draft can't reach the
  event log or SSE broadcast even in a code path nobody wrote a runtime test
  for.
- Behavioral: driving the real `/branch-suggestions` route end to end and
  asserting zero rows land in `teaching_session_events` or
  `precomputed_branches` afterwards.
"""

from __future__ import annotations

import inspect
import os
from functools import partial
from typing import TYPE_CHECKING
from uuid import uuid4

import anyio
import pytest
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from services.gateway.auth.models import Role, User
from services.gateway.models import Base
from services.gateway.routers import teaching_session_live
from services.gateway.routers.teaching_session_live import router
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_session import service
from services.gateway.teaching_session.branches import BranchSource, PrecomputedBranch
from services.gateway.teaching_session.models import (
    RetentionTier,
    TeachingSession,
    TeachingSessionEvent,
)
from services.gateway.teaching_session.tokens import SessionRole, mint_session_token

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

os.environ.setdefault("REDIS_URL", "redis://:omc_redis_secret@localhost:6379")
os.environ["REDIS_URL"] = "redis://:omc_redis_secret@localhost:6379"

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"
OWNER = User(
    user_id="teacher-branches-router", username="teacher-branches-router", role=Role.TEACHER,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    anyio.run(_skip_if_schema_missing)
    app = FastAPI()
    app.include_router(router, prefix="/teaching-sessions")

    async def override_session() -> AsyncIterator:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
        await engine.dispose()

    app.dependency_overrides[get_teaching_pack_session] = override_session
    with TestClient(app) as test_client:
        yield test_client


async def _skip_if_schema_missing() -> None:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async with engine.begin() as connection:
        existing_tables = await connection.run_sync(lambda c: set(Base.metadata.tables))
        if "public.precomputed_branches" not in existing_tables:
            pytest.skip("precomputed_branches table is not present — run alembic upgrade head")
    await engine.dispose()


async def _create_session(*, deck_id: str | None = None) -> TeachingSession:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        created = await service.create_session(
            db,
            session_id=f"branches-live-{uuid4()}",
            teacher_id=OWNER.user_id,
            deck_id=deck_id or f"deck-{uuid4()}",
            snapshot_id="snap-1",
            retention_tier=RetentionTier.AGGREGATE,
        )
        await db.commit()
    await engine.dispose()
    return created


async def _insert_precomputed_branch(*, deck_id: str, slide_id: str) -> str:
    from services.gateway.teaching_session.branches import (
        BranchContentType,
        create_precomputed_branch,
    )

    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        created = await create_precomputed_branch(
            db, deck_id=deck_id, slide_id=slide_id, branch_type=BranchContentType.HINT,
            label="Give a hint", body="Think step by step about the pattern.",
            created_by="teacher-1",
        )
        await db.commit()
    await engine.dispose()
    assert isinstance(created, PrecomputedBranch)
    return created.branch_id


async def _events_for(session_id: str) -> list[TeachingSessionEvent]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(
            select(TeachingSessionEvent)
            .where(TeachingSessionEvent.session_id == session_id)
            .order_by(TeachingSessionEvent.sequence),
        )
        rows = list(result.scalars().all())
    await engine.dispose()
    return rows


async def _branches_for(deck_id: str) -> list[PrecomputedBranch]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        result = await db.execute(
            select(PrecomputedBranch).where(PrecomputedBranch.deck_id == deck_id),
        )
        rows = list(result.scalars().all())
    await engine.dispose()
    return rows


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Structural guard: an AI suggestion can never reach the event log/broadcast.
# ---------------------------------------------------------------------------


class TestStructuralNoRawLeakageGuard:
    def test_suggest_branch_content_never_references_event_log_or_broadcast(self) -> None:
        code_source = inspect.getsource(teaching_session_live.suggest_branch_content)
        for forbidden in ("record_event", "live_sync", "publish_event", "PrecomputedBranch("):
            assert forbidden not in code_source, (
                f"suggest_branch_content must never reference {forbidden!r} -- "
                "a raw AI draft must stay in the HTTP response only"
            )


# ---------------------------------------------------------------------------
# Behavioral: precomputed listing (zero-latency default)
# ---------------------------------------------------------------------------


class TestGetPrecomputedBranches:
    def test_lists_precomputed_branches_for_the_current_slide(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        anyio.run(partial(_insert_precomputed_branch, deck_id=session.deck_id, slide_id="slide-1"))
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.get(
            f"/teaching-sessions/{session.session_id}/branches",
            params={"slide_id": "slide-1"},
            headers=_bearer(token),
        )

        assert response.status_code == 200
        branches = response.json()["branches"]
        assert len(branches) == 1
        assert branches[0]["label"] == "Give a hint"
        assert branches[0]["branch_type"] == "hint"

    def test_a_student_token_cannot_list_branches(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.get(
            f"/teaching-sessions/{session.session_id}/branches",
            params={"slide_id": "slide-1"},
            headers=_bearer(token),
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Behavioral: on-the-fly AI suggestion -- teacher-only draft, never persisted
# ---------------------------------------------------------------------------


class TestSuggestBranchContent:
    def _stub_rewrite(
        self, monkeypatch: pytest.MonkeyPatch, *, returns: str | None = "A simpler retelling.",
    ) -> None:
        async def fake_rewrite(*, run_id: str, current_body: str, instruction: str) -> str | None:
            return returns
        monkeypatch.setattr(
            teaching_session_live, "generate_slide_deck_block_rewrite", fake_rewrite,
        )

    def test_returns_a_before_after_draft_and_persists_nothing(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._stub_rewrite(monkeypatch)
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/branch-suggestions",
            json={
                "slide_id": "slide-1",
                "current_body": "A fraction is part of a whole.",
                "preset": "shorter",
            },
            headers=_bearer(token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body == {
            "slide_id": "slide-1",
            "before": "A fraction is part of a whole.",
            "after": "A simpler retelling.",
        }

        # No session event, no precomputed-branch row -- a raw AI draft never
        # becomes visible to any student/display connection by itself.
        assert anyio.run(_events_for, session.session_id) == []
        assert anyio.run(_branches_for, session.deck_id) == []

    def test_a_student_token_cannot_request_a_suggestion(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        self._stub_rewrite(monkeypatch)
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/branch-suggestions",
            json={"slide_id": "slide-1", "current_body": "text", "preset": "shorter"},
            headers=_bearer(token),
        )

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Behavioral: teacher-approved promotion -- the ONLY path to branch_selected
# ---------------------------------------------------------------------------


class TestApplyBranchSuggestion:
    def test_approving_a_suggestion_persists_it_and_records_branch_selected(
        self, client: TestClient,
    ) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.CONTROLLER, minted_by=OWNER)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/branch-suggestions/apply",
            json={
                "slide_id": "slide-1",
                "branch_type": "hint",
                "label": "AI hint",
                "approved_body": "Here is a teacher-approved hint for the class.",
            },
            headers=_bearer(token),
        )

        assert response.status_code == 200
        assert response.json()["current_branch_id"] is not None

        events = anyio.run(_events_for, session.session_id)
        assert len(events) == 1
        assert events[0].event_type == "branch_selected"
        assert events[0].payload["source"] == BranchSource.AI_GENERATED.value
        branch_id = events[0].payload["branch_id"]

        rows = anyio.run(_branches_for, session.deck_id)
        assert len(rows) == 1
        assert rows[0].branch_id == branch_id
        assert rows[0].body == "Here is a teacher-approved hint for the class."
        assert rows[0].source == BranchSource.AI_GENERATED.value

    def test_a_student_token_cannot_apply_a_suggestion(self, client: TestClient) -> None:
        session = anyio.run(_create_session)
        token = mint_session_token(session, role=SessionRole.STUDENT)

        response = client.post(
            f"/teaching-sessions/{session.session_id}/branch-suggestions/apply",
            json={
                "slide_id": "slide-1",
                "branch_type": "hint",
                "label": "AI hint",
                "approved_body": "text",
            },
            headers=_bearer(token),
        )

        assert response.status_code == 403
