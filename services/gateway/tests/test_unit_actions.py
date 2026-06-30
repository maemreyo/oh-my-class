"""Tests for unit action endpoints — approve-all, spawn-anyway, export (td-011).

DB-backed tests are marked with pytest.mark.skip.
Logic-only tests run without infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User
from services.gateway.routers.unit_runs import router
from services.gateway.teaching_pack_db import get_teaching_pack_session

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"

_TEACHER_ID = "teacher-unit-actions-001"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lesson_sequence_json(session_ids: list[str]) -> dict:
    return {
        "schema_version": "lesson_sequence.v1",
        "topic": "Algebra",
        "grade_level": "Grade 6",
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
                "sub_topic": f"Sub {sid}",
                "duration_minutes": 45,
                "learning_objectives": ["Learn things"],
                "bloom_level_primary": "apply",
                "methodology_primary": "concept_map",
            }
            for idx, sid in enumerate(session_ids)
        ],
        "grounding_status": "grounded",
        "confidence": 0.85,
        "rationale": "Standard progression.",
    }


# ---------------------------------------------------------------------------
# test_approve_all_returns_per_child_results
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_approve_all_returns_per_child_results() -> None:
    """POST /units/{id}/approve-all returns a per-child result dict.

    Verifies:
    - Children in AWAITING_APPROVAL with an active gate → "resumed"
    - Children in AWAITING_APPROVAL without an active gate → "skipped: no active gate"
    - Children not in AWAITING_APPROVAL → not included in results
    """
    import anyio
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from services.gateway.models import Run, RunStatus
    from services.gateway.teaching_pack_control_store import (
        GateInterruptCreate,
        TeachingPackControlStore,
    )
    from services.gateway.teaching_pack_types import RunId, TeacherId
    from services.gateway.unit_run_store import (
        UnitParentRunCreate,
        UnitRunStore,
        UnitSessionRunCreate,
    )

    async def _run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        parent_id = RunId(f"unit-approveall-{uuid4()}")
        seq_json = _make_lesson_sequence_json(["B01", "B02", "B03"])

        async with factory() as sess:
            run_store = UnitRunStore(sess)
            await run_store.create_parent_run(UnitParentRunCreate(
                run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                raw_request="Algebra",
                class_info={},
                lesson_sequence=seq_json,
            ))

            # B01: AWAITING_APPROVAL with active gate → should be resumed
            child_b01 = RunId(f"child-{uuid4()}")
            await run_store.create_child_run(UnitSessionRunCreate(
                run_id=child_b01,
                parent_run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                session_id="B01",
                session_index=1,
                raw_request="Algebra S1",
                class_info={},
            ))
            await sess.execute(
                update(Run)
                .where(Run.run_id == str(child_b01))
                .values(status=RunStatus.AWAITING_APPROVAL),
            )
            control = TeachingPackControlStore(sess)
            await control.open_gate(GateInterruptCreate(
                gate_id=f"gate-b01-{uuid4()}",
                run_id=child_b01,
                gate_name="content_approval",
                payload={},
            ))

            # B02: AWAITING_APPROVAL with NO active gate → should be skipped
            child_b02 = RunId(f"child-{uuid4()}")
            await run_store.create_child_run(UnitSessionRunCreate(
                run_id=child_b02,
                parent_run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                session_id="B02",
                session_index=2,
                raw_request="Algebra S2",
                class_info={},
            ))
            await sess.execute(
                update(Run)
                .where(Run.run_id == str(child_b02))
                .values(status=RunStatus.AWAITING_APPROVAL),
            )

            # B03: GENERATING → not in AWAITING_APPROVAL, should be absent from results
            child_b03 = RunId(f"child-{uuid4()}")
            await run_store.create_child_run(UnitSessionRunCreate(
                run_id=child_b03,
                parent_run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                session_id="B03",
                session_index=3,
                raw_request="Algebra S3",
                class_info={},
            ))
            await sess.execute(
                update(Run)
                .where(Run.run_id == str(child_b03))
                .values(status=RunStatus.GENERATING),
            )

            await sess.commit()

        app_local = FastAPI()
        app_local.include_router(router)

        async def override_session():
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
            assert results["B01"] == "resumed"
            assert results["B02"] == "skipped: no active gate"
            assert "B03" not in results

        # Cleanup
        from sqlalchemy import delete
        from services.gateway.models import Run
        async with factory() as sess:
            await sess.execute(delete(Run).where(Run.parent_run_id == str(parent_id)))
            await sess.execute(delete(Run).where(Run.run_id == str(parent_id)))
            await sess.commit()

        await engine.dispose()

    anyio.run(_run)


# ---------------------------------------------------------------------------
# test_spawn_anyway_creates_child_run
# ---------------------------------------------------------------------------


@pytest.mark.skip("requires real DB + running app")
def test_spawn_anyway_creates_child_run() -> None:
    """POST /units/{id}/sessions/{sid}/spawn-anyway creates a child run + job."""
    import anyio
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from services.gateway.models import Run
    from services.gateway.teaching_pack_job_store import TeachingPackJobStore
    from services.gateway.teaching_pack_models import RunJobStatus
    from services.gateway.teaching_pack_types import RunId, TeacherId
    from services.gateway.unit_run_store import UnitParentRunCreate, UnitRunStore

    async def _run() -> None:
        engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        parent_id = RunId(f"unit-spawn-child-{uuid4()}")
        seq_json = _make_lesson_sequence_json(["C01"])

        async with factory() as sess:
            store = UnitRunStore(sess)
            await store.create_parent_run(UnitParentRunCreate(
                run_id=parent_id,
                teacher_id=TeacherId(_TEACHER_ID),
                raw_request="Algebra",
                class_info={},
                lesson_sequence=seq_json,
            ))
            await sess.commit()

        app_local = FastAPI()
        app_local.include_router(router)

        async def override_session():
            async with factory() as s:
                yield s

        app_local.dependency_overrides[require_teacher] = lambda: User(
            user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
        )
        app_local.dependency_overrides[get_teaching_pack_session] = override_session

        with TestClient(app_local) as client:
            resp = client.post(f"/units/{parent_id}/sessions/C01/spawn-anyway")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "spawned"
            spawned_run_id = data["run_id"]
            assert spawned_run_id

        # Verify child run and job exist in DB
        async with factory() as sess:
            from sqlalchemy import select
            result = await sess.execute(
                select(Run).where(Run.run_id == spawned_run_id),
            )
            child = result.scalar_one_or_none()
            assert child is not None
            assert child.session_id == "C01"
            assert str(child.parent_run_id) == str(parent_id)

            job_store = TeachingPackJobStore(sess)
            idempotency_key = f"spawn-anyway:{parent_id}:C01"
            job = await job_store.find_by_idempotency_key(idempotency_key)
            assert job is not None
            assert job.status in {RunJobStatus.PENDING, RunJobStatus.RUNNING}

        # Cleanup
        from sqlalchemy import delete
        async with factory() as sess:
            await sess.execute(delete(Run).where(Run.parent_run_id == str(parent_id)))
            await sess.execute(delete(Run).where(Run.run_id == str(parent_id)))
            await sess.commit()

        await engine.dispose()

    anyio.run(_run)


# ---------------------------------------------------------------------------
# test_rejected_session_does_not_route_to_empty_export
# ---------------------------------------------------------------------------


def test_rejected_session_does_not_route_to_empty_export() -> None:
    """A REVIEWING child does not count as approved in the aggregate.

    Logic-only test: builds a mocked session to verify that the aggregate
    status reflects in-review sessions as active (not approved), so the unit
    is not presented as ready for export.
    """
    from services.gateway.models import RunStatus
    from services.gateway.routers.unit_runs import _aggregate_status, _display_status

    # REVIEWING → display status is "in_review", not "approved"
    in_review_display = _display_status(RunStatus.REVIEWING)
    assert in_review_display == "in_review"

    # AWAITING_APPROVAL → display status is "in_review", not "approved"
    awaiting_display = _display_status(RunStatus.AWAITING_APPROVAL)
    assert awaiting_display == "in_review"

    # With 3 sessions: 0 approved, 1 failed, 2 active — aggregate is NOT "complete"
    agg = _aggregate_status(total=3, approved=0, failed=1, active=2)
    assert agg != "complete"

    # With 3 sessions: 2 approved, 1 in_review counted as active — not "complete"
    agg2 = _aggregate_status(total=3, approved=2, failed=0, active=1)
    assert agg2 != "complete"

    # Only when all 3 are approved does it become "complete"
    agg3 = _aggregate_status(total=3, approved=3, failed=0, active=0)
    assert agg3 == "complete"


def test_aggregate_status_partially_complete_when_some_failed_none_active() -> None:
    """Aggregate is partially_complete when sessions have mixed approved/failed and no active."""
    from services.gateway.routers.unit_runs import _aggregate_status

    agg = _aggregate_status(total=3, approved=2, failed=1, active=0)
    assert agg == "partially_complete"


def test_aggregate_status_generating_when_active_sessions_exist() -> None:
    """Aggregate is generating when at least one session is active."""
    from services.gateway.routers.unit_runs import _aggregate_status

    agg = _aggregate_status(total=2, approved=0, failed=0, active=2)
    assert agg == "generating"


def test_export_returns_queued_placeholder() -> None:
    """POST /units/{id}/export returns {status: queued} placeholder response."""
    from services.gateway.models import Run, UnitRole

    app_local = FastAPI()
    app_local.include_router(router)
    parent_id = f"unit-export-{uuid4()}"

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

    app_local.dependency_overrides[require_teacher] = lambda: User(
        user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
    )
    app_local.dependency_overrides[get_teaching_pack_session] = override_session

    with TestClient(app_local) as client:
        resp = client.post(f"/units/{parent_id}/export")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["parent_run_id"] == parent_id


def test_spawn_anyway_unknown_session_returns_404() -> None:
    """POST /units/{id}/sessions/UNKNOWN/spawn-anyway returns 404 when session not in sequence."""
    from services.gateway.models import Run, UnitRole

    app_local = FastAPI()
    app_local.include_router(router)
    parent_id = f"unit-spawn-404-{uuid4()}"
    seq_json = _make_lesson_sequence_json(["D01"])

    mock_run = MagicMock(spec=Run)
    mock_run.run_id = parent_id
    mock_run.teacher_id = _TEACHER_ID
    mock_run.unit_role = UnitRole.UNIT_PARENT
    mock_run.raw_request = "Algebra"
    mock_run.class_info = {}
    mock_run.retention_days = None

    mock_session = AsyncMock()

    # First execute() call → returns the parent run (ownership check)
    # Second execute() call → returns None for lesson_sequence (already in mock_run)
    mock_parent_result = MagicMock()
    mock_parent_result.scalar_one_or_none.return_value = mock_run

    mock_seq_result = MagicMock()
    mock_seq_result.scalar_one_or_none.return_value = seq_json

    # list_children returns empty — no existing children
    mock_children_result = MagicMock()
    mock_children_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(
        side_effect=[mock_parent_result, mock_seq_result, mock_children_result],
    )

    async def override_session():
        yield mock_session

    app_local.dependency_overrides[require_teacher] = lambda: User(
        user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
    )
    app_local.dependency_overrides[get_teaching_pack_session] = override_session

    with TestClient(app_local, raise_server_exceptions=False) as client:
        resp = client.post(f"/units/{parent_id}/sessions/NONEXISTENT/spawn-anyway")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "session_not_found"


def test_approve_all_returns_empty_results_when_no_awaiting_approval_children() -> None:
    """POST /units/{id}/approve-all returns empty results dict when no children are AWAITING_APPROVAL."""
    from services.gateway.models import Run, RunStatus, UnitRole

    app_local = FastAPI()
    app_local.include_router(router)
    parent_id = f"unit-approveall-empty-{uuid4()}"

    mock_run = MagicMock(spec=Run)
    mock_run.run_id = parent_id
    mock_run.teacher_id = _TEACHER_ID
    mock_run.unit_role = UnitRole.UNIT_PARENT

    # Build a mock child with GENERATING status
    mock_child = MagicMock()
    mock_child.run_id = f"child-{uuid4()}"
    mock_child.parent_run_id = parent_id
    mock_child.session_id = "E01"
    mock_child.session_index = 1
    mock_child.status = RunStatus.GENERATING
    mock_child.raw_request = "Test"

    mock_session = AsyncMock()

    mock_parent_result = MagicMock()
    mock_parent_result.scalar_one_or_none.return_value = mock_run

    mock_children_result = MagicMock()
    mock_children_result.scalars.return_value.all.return_value = [mock_child]

    mock_session.execute = AsyncMock(
        side_effect=[mock_parent_result, mock_children_result],
    )
    mock_session.commit = AsyncMock()

    async def override_session():
        yield mock_session

    app_local.dependency_overrides[require_teacher] = lambda: User(
        user_id=_TEACHER_ID, username="t", role=Role.TEACHER,
    )
    app_local.dependency_overrides[get_teaching_pack_session] = override_session

    with TestClient(app_local) as client:
        resp = client.post(f"/units/{parent_id}/approve-all")
        assert resp.status_code == 200
        assert resp.json()["results"] == {}
