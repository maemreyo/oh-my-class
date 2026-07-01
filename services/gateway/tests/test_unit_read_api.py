"""Tests for the unit read API — GET /units/{parent_run_id} and SSE (td-011).

All tests that require a real DB + running app are marked with
pytest.mark.skip so the suite stays green without infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers.unit_runs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

_TEACHER_ID = "teacher-unit-read-001"
_OTHER_TEACHER_ID = "teacher-unit-read-999"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_lesson_sequence_json(session_ids: list[str] | None = None) -> dict[str, object]:
    if session_ids is None:
        session_ids = ["S01", "S02", "S03"]
    return {
        "schema_version": "lesson_sequence.v1",
        "topic": "Fractions",
        "grade_level": "Grade 5",
        "subject": "Math",
        "locale": "en",
        "total_sessions": len(session_ids),
        "total_duration_minutes": len(session_ids) * 45,
        "sessions": [
            {
                "schema_version": "lesson_sequence.v1",
                "session_id": sid,
                "order_index": idx + 1,
                "title": f"Session {sid}",
                "sub_topic": f"Sub-topic {sid}",
                "duration_minutes": 45,
                "learning_objectives": ["Understand basics"],
                "bloom_level_primary": "understand",
                "methodology_primary": "concept_map",
            }
            for idx, sid in enumerate(session_ids)
        ],
        "grounding_status": "grounded",
        "confidence": 0.9,
        "rationale": "Well-structured progression.",
    }


@pytest.fixture
def app() -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    return application


# ---------------------------------------------------------------------------
# test_get_unit_view_returns_counts
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_get_unit_view_returns_counts() -> None:
    """GET /units/{id} returns correct session counts against a real DB."""
    import anyio
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from services.gateway.unit_run_store import (
        UnitParentRunCreate,
        UnitRunStore,
    )
    from services.gateway.teaching_pack_types import RunId, TeacherId

    async def _run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        parent_id = RunId(f"unit-read-api-{uuid4()}")
        seq_json = _make_lesson_sequence_json(["S01", "S02"])
        async with factory() as sess:
            store = UnitRunStore(sess)
            await store.create_parent_run(UnitParentRunCreate(
                run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                raw_request="Fractions",
                class_info={"topic": "Fractions"},
                lesson_sequence=seq_json,
            ))
            await sess.commit()

        app_local = FastAPI()
        app_local.include_router(router)

        async def override_session() -> "AsyncIterator[AsyncSession]":
            async with factory() as s:
                yield s

        app_local.dependency_overrides[require_teacher] = lambda: User(
            user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
        )
        app_local.dependency_overrides[get_teaching_pack_session] = override_session

        with TestClient(app_local) as client:
            resp = client.get(f"/units/{parent_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["aggregate"]["total_sessions"] == 2
            assert data["aggregate"]["approved_sessions"] == 0
            assert len(data["sessions"]) == 2

        # Clean up
        from sqlalchemy import delete
        from services.gateway.models import Run
        async with factory() as sess:
            await sess.execute(delete(Run).where(Run.run_id == str(parent_id)))
            await sess.commit()

        await engine.dispose()

    anyio.run(_run)


# ---------------------------------------------------------------------------
# test_cross_teacher_access_denied
# ---------------------------------------------------------------------------


def test_cross_teacher_access_denied(app: FastAPI) -> None:
    """A different teacher_id gets 403 on GET /units/{id}."""
    from services.gateway.models import Run, UnitRole

    parent_id = f"unit-xowner-{uuid4()}"

    # Create a mock parent Run owned by _TEACHER_ID
    mock_run = MagicMock(spec=Run)
    mock_run.run_id = parent_id
    mock_run.teacher_id = _TEACHER_ID
    mock_run.unit_role = UnitRole.UNIT_PARENT
    mock_run.lesson_sequence = _make_lesson_sequence_json()
    mock_run.raw_request = "Fractions"
    mock_run.class_info = {}
    mock_run.retention_days = None

    mock_session = AsyncMock()

    async def override_session():
        yield mock_session

    # Simulate DB returning the run
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id=_OTHER_TEACHER_ID, username="other", role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get(f"/units/{parent_id}")
        assert resp.status_code == 403
        assert resp.json()["detail"] == "not_unit_owner"


# ---------------------------------------------------------------------------
# test_unit_sse_emits_session_changed
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_unit_sse_emits_session_changed() -> None:
    """SSE stream emits unit.progress events after a status change.

    This test would:
    1. Create a unit parent run with children in the real DB.
    2. Open the SSE stream in a background thread.
    3. Trigger a status change on a child run.
    4. Assert the SSE stream yields an event with event_type=unit.progress.
    """
    # Full end-to-end test requiring a live app + DB.
    raise NotImplementedError("integrate with running gateway")


def test_unit_sse_endpoint_returns_event_stream(app: FastAPI) -> None:
    """GET /units/{id}/status returns text/event-stream with ownership check.

    The SSE generator runs indefinitely; we verify only the response headers
    by checking that the endpoint wires up correctly without consuming events.
    """
    from services.gateway.models import Run, UnitRole

    parent_id = f"unit-sse-{uuid4()}"

    mock_run = MagicMock(spec=Run)
    mock_run.run_id = parent_id
    mock_run.teacher_id = _TEACHER_ID
    mock_run.unit_role = UnitRole.UNIT_PARENT

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_session():
        yield mock_session

    app.dependency_overrides[require_teacher] = lambda: User(
        user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
    )
    app.dependency_overrides[get_teaching_pack_session] = override_session

    # Patch the generator so it yields one heartbeat and stops immediately,
    # allowing TestClient to complete the request without hanging.
    async def _finite_generator(*_args, **_kwargs):
        yield ": heartbeat\n\n"

    with patch(
        "services.gateway.routers.unit_runs._unit_sse_generator",
        side_effect=_finite_generator,
    ):
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get(f"/units/{parent_id}/status")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


def test_unit_sse_cross_teacher_denied() -> None:
    """SSE GET /units/{id}/status returns 403 for wrong teacher."""
    from services.gateway.models import Run, UnitRole

    parent_id = f"unit-sse-xowner-{uuid4()}"

    mock_run = MagicMock(spec=Run)
    mock_run.run_id = parent_id
    mock_run.teacher_id = _TEACHER_ID  # owned by _TEACHER_ID
    mock_run.unit_role = UnitRole.UNIT_PARENT

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_run
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_session():
        yield mock_session

    # Request comes from _OTHER_TEACHER_ID — the ownership check raises 403
    # before any generator is invoked.
    app2 = FastAPI()
    from services.gateway.routers.unit_runs import router as unit_router
    app2.include_router(unit_router)
    app2.dependency_overrides[require_teacher] = lambda: User(
        user_id=_OTHER_TEACHER_ID, username="other", role=Role.TEACHER,
    )
    app2.dependency_overrides[get_teaching_pack_session] = override_session

    with TestClient(app2, raise_server_exceptions=False) as client:
        resp = client.get(f"/units/{parent_id}/status")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# test_approve_all_partial_success
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_approve_all_partial_success() -> None:
    """One child approve fails, others succeed — real DB integration test."""
    import anyio
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from services.gateway.models import Run, RunStatus
    from services.gateway.unit_run_store import (
        UnitParentRunCreate,
        UnitRunStore,
        UnitSessionRunCreate,
    )
    from services.gateway.teaching_pack_control_store import (
        GateInterruptCreate,
        TeachingPackControlStore,
    )
    from services.gateway.teaching_pack_types import RunId, TeacherId

    async def _run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        parent_id = RunId(f"unit-approve-partial-{uuid4()}")
        seq_json = _make_lesson_sequence_json(["A01", "A02"])

        async with factory() as sess:
            run_store = UnitRunStore(sess)
            await run_store.create_parent_run(UnitParentRunCreate(
                run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                raw_request="Fractions",
                class_info={},
                lesson_sequence=seq_json,
            ))
            # Create first child with AWAITING_APPROVAL + active gate
            child1_id = RunId(f"child-{uuid4()}")
            await run_store.create_child_run(UnitSessionRunCreate(
                run_id=child1_id,
                parent_run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                session_id="A01",
                session_index=1,
                raw_request="Fractions S1",
                class_info={},
            ))
            from sqlalchemy import update
            await sess.execute(
                update(Run)
                .where(Run.run_id == str(child1_id))
                .values(status=RunStatus.AWAITING_APPROVAL),
            )
            control = TeachingPackControlStore(sess)
            await control.open_gate(GateInterruptCreate(
                gate_id=f"gate-{uuid4()}",
                run_id=child1_id,
                gate_name="content_approval",
                payload={},
            ))
            # Second child: AWAITING_APPROVAL but NO active gate (should return skipped)
            child2_id = RunId(f"child-{uuid4()}")
            await run_store.create_child_run(UnitSessionRunCreate(
                run_id=child2_id,
                parent_run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                session_id="A02",
                session_index=2,
                raw_request="Fractions S2",
                class_info={},
            ))
            await sess.execute(
                update(Run)
                .where(Run.run_id == str(child2_id))
                .values(status=RunStatus.AWAITING_APPROVAL),
            )
            await sess.commit()

        app_local = FastAPI()
        app_local.include_router(router)

        async def override_session() -> "AsyncIterator[AsyncSession]":
            async with factory() as s:
                yield s

        app_local.dependency_overrides[require_teacher] = lambda: User(
            user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
        )
        app_local.dependency_overrides[get_teaching_pack_session] = override_session

        with TestClient(app_local) as client:
            resp = client.post(f"/units/{parent_id}/approve-all")
            assert resp.status_code == 200
            results = resp.json()["results"]
            assert results["A01"] == "resumed"
            assert results["A02"] == "skipped: no active gate"

        # Cleanup
        from sqlalchemy import delete
        async with factory() as sess:
            await sess.execute(delete(Run).where(Run.parent_run_id == str(parent_id)))
            await sess.execute(delete(Run).where(Run.run_id == str(parent_id)))
            await sess.commit()

        await engine.dispose()

    anyio.run(_run)


# ---------------------------------------------------------------------------
# test_spawn_anyway_unblocks
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_spawn_anyway_unblocks() -> None:
    """spawn-anyway creates and starts a blocked (un-spawned) session."""
    import anyio
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from services.gateway.unit_run_store import UnitParentRunCreate, UnitRunStore
    from services.gateway.teaching_pack_types import RunId, TeacherId

    async def _run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        parent_id = RunId(f"unit-spawn-{uuid4()}")
        seq_json = _make_lesson_sequence_json(["SP01"])

        async with factory() as sess:
            run_store = UnitRunStore(sess)
            await run_store.create_parent_run(UnitParentRunCreate(
                run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                raw_request="Fractions",
                class_info={},
                lesson_sequence=seq_json,
            ))
            await sess.commit()

        app_local = FastAPI()
        app_local.include_router(router)

        async def override_session() -> "AsyncIterator[AsyncSession]":
            async with factory() as s:
                yield s

        app_local.dependency_overrides[require_teacher] = lambda: User(
            user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
        )
        app_local.dependency_overrides[get_teaching_pack_session] = override_session

        with TestClient(app_local) as client:
            # Session SP01 has no child run yet — spawn-anyway should create one.
            resp = client.post(f"/units/{parent_id}/sessions/SP01/spawn-anyway")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "spawned"
            assert data["run_id"]

            # Idempotent: second call returns already_spawned
            resp2 = client.post(f"/units/{parent_id}/sessions/SP01/spawn-anyway")
            assert resp2.status_code == 200
            assert resp2.json()["status"] == "already_spawned"

        # Cleanup
        from sqlalchemy import delete
        from services.gateway.models import Run
        async with factory() as sess:
            await sess.execute(delete(Run).where(Run.parent_run_id == str(parent_id)))
            await sess.execute(delete(Run).where(Run.run_id == str(parent_id)))
            await sess.commit()

        await engine.dispose()

    anyio.run(_run)
