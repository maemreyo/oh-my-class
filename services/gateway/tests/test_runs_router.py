"""Tests for runs_router — create, get, and SSE stream endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# jwt is not installed in the test environment — inject before gateway imports
if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.middleware.error_handler import register_exception_handlers  # noqa: E402
from services.gateway.routers.runs import (  # noqa: E402
    RunRequest,
    RunResponse,
    _derive_status,
    _event_store,
    _event_subscribers,
    _to_run_response,
    build_initial_state,
    emit_run_event,
    get_run_events,
    router,
)

# ── helpers ───────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_event_store():
    _event_store.clear()
    _event_subscribers.clear()
    yield
    _event_store.clear()
    _event_subscribers.clear()


MOCK_STATE = {
    "raw_request": "Teach photosynthesis",
    "teacher_id": "t-001",
    "class_info": {"grade": 5},
    "run_id": "mock-run-id",
    "blueprint_approved": False,
    "research_policy": "standard",
    "artifact_types": [],
    "theme": "default",
    "artifacts": [],
    "quality_passed": False,
    "teacher_approved": False,
    "revision_count": 0,
    "export_formats": ["html"],
    "exported_files": [],
    "current_step": 3,
    "tokens_used": 0,
    "cost_usd": 0.0,
}


async def _mock_ainvoke(
    state: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {**state, "current_step": 3}


def _make_mock_graph() -> MagicMock:
    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=_mock_ainvoke)
    return graph


def _make_failing_graph(error_msg: str = "Graph exploded") -> MagicMock:
    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=RuntimeError(error_msg))
    return graph


def _make_teacher(user_id: str = "t-001", username: str = "teacher1") -> User:
    return User(user_id=user_id, username=username, role=Role.TEACHER)


def _make_admin() -> User:
    return User(user_id="admin-001", username="admin1", role=Role.ADMIN)


def _make_app_with_auth(user: User | None = None) -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)

    app.state.graph = _make_mock_graph()
    app.state.runs = {}

    teacher = user or _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


def _make_app_no_auth() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/run")
    return TestClient(app)


def _make_app_with_failing_graph() -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)

    app.state.graph = _make_failing_graph()
    app.state.runs = {}

    teacher = _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


# ── build_initial_state ──────────────────────────────────────────────────────


class TestBuildInitialState:
    def test_creates_complete_state_dict(self):
        req = RunRequest(
            raw_request="Teach photosynthesis",
            class_info={"grade": 5, "subject": "science"},
            teacher_id="t-001",
        )
        state = build_initial_state(req, "run-123")

        assert state["raw_request"] == "Teach photosynthesis"
        assert state["teacher_id"] == "t-001"
        assert state["class_info"] == {"grade": 5, "subject": "science"}
        assert state["run_id"] == "run-123"
        assert state["blueprint_approved"] is False
        assert state["research_policy"] == "standard"
        assert state["artifact_types"] == []
        assert state["theme"] == "default"
        assert state["artifacts"] == []
        assert state["quality_passed"] is False
        assert state["teacher_approved"] is False
        assert state["revision_count"] == 0
        assert state["export_formats"] == ["html"]
        assert state["exported_files"] == []
        assert state["current_step"] == 1
        assert state["tokens_used"] == 0
        assert state["cost_usd"] == 0.0

    def test_rejects_missing_raw_request(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RunRequest(class_info={}, teacher_id="t-001")  # type: ignore[call-arg]


# ── create_run ────────────────────────────────────────────────────────────────


class TestCreateRun:
    def test_create_run_returns_200(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {"grade": 5},
            "teacher_id": "t-001",
        })
        assert response.status_code == 200

    def test_create_run_returns_run_id(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach math",
            "class_info": {"grade": 3},
            "teacher_id": "t-001",
        })
        data = response.json()
        assert "run_id" in data
        assert len(data["run_id"]) > 0

    def test_create_run_returns_running_status(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach science",
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.json()["status"] == "running"

    def test_create_run_returns_state_dict(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach science",
            "class_info": {},
            "teacher_id": "t-001",
        })
        data = response.json()
        assert data["state"] is not None
        assert "current_step" in data["state"]
        assert data["state"]["current_step"] == 3
        assert data["state"]["raw_request"] == "Teach science"

    def test_create_run_generates_unique_ids(self):
        client = _make_app_with_auth()
        payload = {"raw_request": "Teach X", "class_info": {}, "teacher_id": "t-001"}
        r1 = client.post("/run", json=payload)
        r2 = client.post("/run", json=payload)
        assert r1.json()["run_id"] != r2.json()["run_id"]

    def test_create_run_persists_run_in_store(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = response.json()["run_id"]
        app: FastAPI = client.app  # type: ignore[assignment]
        assert run_id in app.state.runs
        assert app.state.runs[run_id]["status"] == "running"

    def test_create_run_graph_failure_returns_500(self):
        client = _make_app_with_failing_graph()
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.status_code == 500
        data = response.json()
        assert data["error_code"] == "PIPELINE_ERROR"

    def test_create_run_requires_auth(self):
        client = _make_app_no_auth()
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.status_code in (401, 403, 422)

    def test_create_run_rejects_missing_fields(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.status_code == 422


# ── get_run ───────────────────────────────────────────────────────────────────


class TestGetRun:
    def test_get_run_returns_200_after_create(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}")
        assert response.status_code == 200

    def test_get_run_returns_correct_run_id(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}")
        assert response.json()["run_id"] == run_id

    def test_get_run_returns_state_and_status(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}")
        data = response.json()
        assert "status" in data
        assert "state" in data
        assert data["state"]["raw_request"] == "Teach X"

    def test_get_run_not_found_returns_404(self):
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent-run-id")
        assert response.status_code == 404
        data = response.json()
        assert data["error_code"] == "NOT_FOUND"

    def test_get_run_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/test-run-123")
        assert response.status_code in (401, 403, 422)


# ── get_run_status (SSE) ─────────────────────────────────────────────────────


class TestGetRunStatus:
    def test_sse_returns_200_for_existing_run(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert response.status_code == 200

    def test_sse_returns_404_for_unknown_run(self):
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent-run/status")
        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND"

    def test_sse_content_type_is_event_stream(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert "text/event-stream" in response.headers["content-type"]

    def test_sse_has_cache_control_header(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert response.headers.get("cache-control") == "no-cache"

    def test_sse_contains_run_created_event(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert "run_created" in response.text

    def test_sse_contains_step_completed_event(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert "step_completed" in response.text

    def test_sse_event_has_required_fields(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        response = client.get(f"/run/{run_id}/status")
        assert f'"run_id":"{run_id}"' in response.text
        assert '"event_type"' in response.text or "event: " in response.text
        assert '"timestamp"' in response.text

    def test_sse_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/test-run-123/status")
        assert response.status_code in (401, 403, 422)


# ── RunRequest / RunResponse models ─────────────────────────────────────────


class TestRunModels:
    def test_run_request_has_required_fields(self):
        req = RunRequest(raw_request="Teach X", class_info={}, teacher_id="t-001")
        assert req.teacher_id == "t-001"

    def test_run_response_has_required_fields(self):
        resp = RunResponse(run_id="r-1", status="created")
        assert resp.run_id == "r-1"
        assert resp.state is None
        assert resp.topic is None
        assert resp.current_step is None
        assert resp.artifact_types is None


# ── _to_run_response (read model mapper) ────────────────────────────────────


class TestToRunResponse:
    def test_extracts_topic_from_lesson_plan(self):
        run_data = {
            "run_id": "r-1",
            "status": "awaiting_approval",
            "state": {
                "lesson_plan": {"topic": "Photosynthesis"},
                "current_step": 4,
                "artifact_types": ["lesson", "worksheet"],
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.run_id == "r-1"
        assert result.status == "awaiting_approval"
        assert result.topic == "Photosynthesis"
        assert result.current_step == 4
        assert result.artifact_types == ["lesson", "worksheet"]

    def test_handles_missing_lesson_plan(self):
        run_data = {
            "run_id": "r-2",
            "status": "running",
            "state": {
                "current_step": 1,
                "artifact_types": [],
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.topic is None
        assert result.current_step == 1
        assert result.artifact_types is None  # empty list maps to None

    def test_handles_empty_state(self):
        run_data = {
            "run_id": "r-3",
            "status": "running",
            "state": {},
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.topic is None
        assert result.current_step is None
        assert result.artifact_types is None
        assert result.state is None  # empty state maps to None


# ── list_runs ───────────────────────────────────────────────────────────────


class TestRunResponseQuality:
    def test_initial_run_has_no_quality(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {"grade": 5},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        get_resp = client.get(f"/run/{run_id}")
        state = get_resp.json()["state"]
        assert state.get("quality") is None

    def test_quality_field_appears_after_schema_pass(self):
        run_data = {
            "run_id": "r-q1",
            "status": "running",
            "state": {
                "current_step": 9,
                "artifact_types": ["lesson"],
                "schema_valid": True,
                "artifacts": [{"type": "lesson", "content": "Plants use sunlight."}],
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.state is not None
        quality = result.state["quality"]
        assert quality["schema_valid"] is True

    def test_quality_field_appears_after_judge_score(self):
        run_data = {
            "run_id": "r-q2",
            "status": "running",
            "state": {
                "current_step": 10,
                "artifact_types": ["lesson"],
                "schema_valid": True,
                "content_review_passed": True,
                "judge_score": 8.5,
                "quality_passed": True,
                "artifacts": [{"type": "lesson", "content": "Content."}],
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.state is not None
        quality = result.state["quality"]
        assert quality["schema_valid"] is True
        assert quality["content_review_passed"] is True
        assert quality["judge_score"] == 8.5
        assert quality["passed"] is True

    def test_quality_field_includes_healing_strategy(self):
        run_data = {
            "run_id": "r-q3",
            "status": "running",
            "state": {
                "current_step": 9,
                "artifact_types": ["lesson"],
                "schema_valid": False,
                "healing_strategy": "rewrite",
                "fail_count": 1,
                "fail_context": {"errors": ["missing keys"]},
                "artifacts": [],
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.state is not None
        quality = result.state["quality"]
        assert quality["schema_valid"] is False
        assert quality["healing_strategy"] == "rewrite"
        assert quality["fail_count"] == 1
        assert quality["fail_context"] == {"errors": ["missing keys"]}

    def test_quality_none_when_no_quality_fields(self):
        run_data = {
            "run_id": "r-q4",
            "status": "running",
            "state": {"current_step": 1, "artifact_types": []},
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.state is not None
        assert "quality" not in result.state

    def test_top_level_fields_preserved_with_quality(self):
        run_data = {
            "run_id": "r-q5",
            "status": "awaiting_approval",
            "state": {
                "lesson_plan": {"topic": "Math"},
                "current_step": 11,
                "artifact_types": ["lesson", "quiz"],
                "judge_score": 8.0,
            },
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        result = _to_run_response(run_data)
        assert result.topic == "Math"
        assert result.current_step == 11
        assert result.artifact_types == ["lesson", "quiz"]
        assert result.state is not None
        assert result.state["quality"]["judge_score"] == 8.0


class TestListRuns:
    def test_list_runs_returns_empty_array_initially(self):
        client = _make_app_with_auth()
        response = client.get("/run")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_runs_returns_created_runs(self):
        client = _make_app_with_auth()
        # Create a run
        create_resp = client.post("/run", json={
            "raw_request": "Teach math",
            "class_info": {"grade": 3},
            "teacher_id": "t-001",
        })
        assert create_resp.status_code == 200
        created_run_id = create_resp.json()["run_id"]

        # List runs — should include the created run
        list_resp = client.get("/run")
        assert list_resp.status_code == 200
        runs = list_resp.json()
        assert len(runs) == 1
        assert runs[0]["run_id"] == created_run_id
        assert runs[0]["status"] == "running"

    def test_list_runs_filters_by_teacher(self):
        teacher1 = _make_teacher(user_id="t-001", username="teacher1")
        teacher2 = _make_teacher(user_id="t-002", username="teacher2")

        # Teacher 1's app
        app1 = _make_app_with_auth(teacher1)
        app1.post("/run", json={
            "raw_request": "Teach A",
            "class_info": {},
            "teacher_id": "t-001",
        })

        # Teacher 2's app — shares the same runs store
        app2_client = _make_app_with_auth(teacher2)
        # Copy runs from app1 to app2 so they share data
        app2_client.app.state.runs = app1.app.state.runs  # type: ignore[attr-defined]
        app2_client.post("/run", json={
            "raw_request": "Teach B",
            "class_info": {},
            "teacher_id": "t-002",
        })

        # Teacher 1 sees only their run
        list1 = app1.get("/run")
        assert list1.status_code == 200
        runs1 = list1.json()
        assert len(runs1) == 1
        assert runs1[0]["state"]["raw_request"] == "Teach A"

        # Teacher 2 sees only their run
        list2 = app2_client.get("/run")
        assert list2.status_code == 200
        runs2 = list2.json()
        assert len(runs2) == 1
        assert runs2[0]["state"]["raw_request"] == "Teach B"

    def test_list_runs_admin_sees_all(self):
        admin = _make_admin()
        client = _make_app_with_auth(admin)

        # Create runs as teacher
        teacher = _make_teacher()
        teacher_client = _make_app_with_auth(teacher)
        teacher_client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        teacher_client.post("/run", json={
            "raw_request": "Teach Y",
            "class_info": {},
            "teacher_id": "t-001",
        })

        # Share runs store with admin
        client.app.state.runs = teacher_client.app.state.runs  # type: ignore[attr-defined]

        # Admin sees all runs
        list_resp = client.get("/run")
        assert list_resp.status_code == 200
        runs = list_resp.json()
        assert len(runs) == 2

    def test_list_runs_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run")
        assert response.status_code in (401, 403, 422)

    def test_list_runs_response_schema(self):
        client = _make_app_with_auth()
        client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {"grade": 5},
            "teacher_id": "t-001",
        })
        list_resp = client.get("/run")
        runs = list_resp.json()
        assert len(runs) == 1
        run = runs[0]
        # Verify schema matches RunResponse
        assert isinstance(run["run_id"], str)
        assert isinstance(run["status"], str)
        # Optional fields present (may be None)
        assert "topic" in run or "state" in run
        # Verify full response validates as RunResponse
        validated = RunResponse(**run)
        assert validated.run_id == run["run_id"]


# ── Progress stream (event store + SSE) ────────────────────────────────────


class TestProgressStream:
    def test_emit_run_event_stores_events(self):
        emit_run_event("run-1", "run_created", {"status": "running"})
        emit_run_event("run-1", "step_completed", {"status": "done"})
        events = get_run_events("run-1")
        assert len(events) == 2
        assert events[0]["event_type"] == "run_created"
        assert events[1]["event_type"] == "step_completed"

    def test_event_store_returns_events_in_order(self):
        for i in range(5):
            emit_run_event("run-ord", "step", {"step": i})
        events = get_run_events("run-ord")
        steps = [e["step"] for e in events]
        assert steps == [0, 1, 2, 3, 4]

    def test_get_run_events_returns_empty_for_unknown_run(self):
        assert get_run_events("nonexistent") == []

    def test_emit_run_event_includes_timestamp(self):
        emit_run_event("run-ts", "run_created", {})
        events = get_run_events("run-ts")
        assert "timestamp" in events[0]
        assert "T" in events[0]["timestamp"]

    def test_emit_run_event_includes_run_id(self):
        emit_run_event("run-rid", "run_created", {})
        events = get_run_events("run-rid")
        assert events[0]["run_id"] == "run-rid"

    def test_emit_run_event_notifies_subscribers(self):
        import asyncio

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        _event_subscribers["run-sub"].append(queue)
        try:
            emit_run_event("run-sub", "run_created", {"status": "running"})
            assert not queue.empty()
            event = queue.get_nowait()
            assert event is not None
            assert event["event_type"] == "run_created"
            assert event["run_id"] == "run-sub"
        finally:
            _event_subscribers["run-sub"].remove(queue)

    def test_emit_run_event_drops_when_queue_full(self):
        import asyncio

        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=1)
        _event_subscribers["run-full"].append(queue)
        try:
            emit_run_event("run-full", "event1", {})
            emit_run_event("run-full", "event2", {})  # should not raise
            assert queue.qsize() == 1
        finally:
            _event_subscribers["run-full"].remove(queue)

    def test_create_run_emits_run_created_event(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach science",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        events = get_run_events(run_id)
        event_types = [e["event_type"] for e in events]
        assert "run_created" in event_types

    def test_create_run_emits_step_completed_event(self):
        client = _make_app_with_auth()
        create_resp = client.post("/run", json={
            "raw_request": "Teach science",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        events = get_run_events(run_id)
        event_types = [e["event_type"] for e in events]
        assert "step_completed" in event_types

    def test_create_run_emits_run_failed_on_graph_error(self):
        client = _make_app_with_failing_graph()
        create_resp = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        events = get_run_events(run_id)
        event_types = [e["event_type"] for e in events]
        assert "run_failed" in event_types
        failed_event = next(e for e in events if e["event_type"] == "run_failed")
        assert "error" in failed_event


# ── Export endpoints ────────────────────────────────────────────────────────

MOCK_EXPORTED_FILES = [
    {
        "artifact_id": "a-1",
        "format": "html",
        "title": "Photosynthesis Lesson",
        "content": (
            "<!DOCTYPE html><html><head>"
            "<title>oh-my-class</title>"
            "</head><body>Lesson</body></html>"
        ),
        "artifact_type": "lesson",
        "theme": "default",
    },
    {
        "artifact_id": "a-2",
        "format": "html",
        "title": "Quiz",
        "content": (
            "<!DOCTYPE html><html><head>"
            "<title>oh-my-class</title>"
            "</head><body>Quiz</body></html>"
        ),
        "artifact_type": "quiz",
        "theme": "default",
    },
]


def _seed_run_with_exports(client: TestClient) -> str:
    from datetime import UTC, datetime

    run_id = "run-export-test"
    client.app.state.runs[run_id] = {
        "run_id": run_id,
        "status": "completed",
        "state": {
            "exported_files": MOCK_EXPORTED_FILES,
            "export_ready": True,
            "current_step": 12,
        },
        "teacher_id": "t-001",
        "created_at": datetime.now(UTC).isoformat(),
    }
    return run_id


class TestListExports:
    def test_list_exports_returns_empty_when_no_exports(self):
        client = _make_app_with_auth()
        client.app.state.runs["run-no-exports"] = {
            "run_id": "run-no-exports",
            "status": "running",
            "state": {"exported_files": []},
            "teacher_id": "t-001",
            "created_at": "2026-01-01T00:00:00",
        }
        response = client.get("/run/run-no-exports/exports")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_exports_returns_metadata(self):
        client = _make_app_with_auth()
        run_id = _seed_run_with_exports(client)
        response = client.get(f"/run/{run_id}/exports")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["artifact_id"] == "a-1"
        assert data[0]["title"] == "Photosynthesis Lesson"
        assert data[0]["format"] == "html"
        assert data[0]["artifact_type"] == "lesson"
        # Content should NOT be in the list response
        assert all("content" not in item for item in data)

    def test_list_exports_not_found_returns_404(self):
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent/exports")
        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND"

    def test_list_exports_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/run-123/exports")
        assert response.status_code in (401, 403, 422)


class TestDownloadExport:
    def test_download_returns_html_content(self):
        client = _make_app_with_auth()
        run_id = _seed_run_with_exports(client)
        response = client.get(f"/run/{run_id}/exports/a-1")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "oh-my-class" in response.text

    def test_download_not_found_returns_404(self):
        client = _make_app_with_auth()
        run_id = _seed_run_with_exports(client)
        response = client.get(f"/run/{run_id}/exports/nonexistent-artifact")
        assert response.status_code == 404
        assert response.json()["error_code"] == "NOT_FOUND"

    def test_download_run_not_found_returns_404(self):
        client = _make_app_with_auth()
        response = client.get("/run/nonexistent/exports/a-1")
        assert response.status_code == 404

    def test_download_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/run-123/exports/a-1")
        assert response.status_code in (401, 403, 422)

    def test_download_second_artifact(self):
        client = _make_app_with_auth()
        run_id = _seed_run_with_exports(client)
        response = client.get(f"/run/{run_id}/exports/a-2")
        assert response.status_code == 200
        assert "Quiz" in response.text


# ── Ownership guard ─────────────────────────────────────────────────────────


class TestOwnershipGuard:
    def test_get_run_denied_for_other_teacher(self):
        teacher1 = _make_teacher(user_id="t-001", username="teacher1")
        teacher2 = _make_teacher(user_id="t-002", username="teacher2")

        client1 = _make_app_with_auth(teacher1)
        create_resp = client1.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]
        client1.app.state.runs[run_id]["teacher_id"] = "t-001"

        client2 = _make_app_with_auth(teacher2)
        client2.app.state.runs = client1.app.state.runs

        response = client2.get(f"/run/{run_id}")
        assert response.status_code == 403
        assert response.json()["error_code"] == "AUTHORIZATION_ERROR"

    def test_get_run_allowed_for_admin(self):
        admin = _make_admin()
        teacher = _make_teacher()

        teacher_client = _make_app_with_auth(teacher)
        create_resp = teacher_client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]

        admin_client = _make_app_with_auth(admin)
        admin_client.app.state.runs = teacher_client.app.state.runs

        response = admin_client.get(f"/run/{run_id}")
        assert response.status_code == 200

    def test_sse_denied_for_other_teacher(self):
        teacher1 = _make_teacher(user_id="t-001", username="teacher1")
        teacher2 = _make_teacher(user_id="t-002", username="teacher2")

        client1 = _make_app_with_auth(teacher1)
        create_resp = client1.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        run_id = create_resp.json()["run_id"]

        client2 = _make_app_with_auth(teacher2)
        client2.app.state.runs = client1.app.state.runs

        response = client2.get(f"/run/{run_id}/status")
        assert response.status_code == 403

    def test_exports_denied_for_other_teacher(self):
        teacher1 = _make_teacher(user_id="t-001", username="teacher1")
        teacher2 = _make_teacher(user_id="t-002", username="teacher2")

        client1 = _make_app_with_auth(teacher1)
        run_id = _seed_run_with_exports(client1)
        client1.app.state.runs[run_id]["teacher_id"] = "t-001"

        client2 = _make_app_with_auth(teacher2)
        client2.app.state.runs = client1.app.state.runs

        response = client2.get(f"/run/{run_id}/exports")
        assert response.status_code == 403

    def test_export_download_denied_for_other_teacher(self):
        teacher1 = _make_teacher(user_id="t-001", username="teacher1")
        teacher2 = _make_teacher(user_id="t-002", username="teacher2")

        client1 = _make_app_with_auth(teacher1)
        run_id = _seed_run_with_exports(client1)
        client1.app.state.runs[run_id]["teacher_id"] = "t-001"

        client2 = _make_app_with_auth(teacher2)
        client2.app.state.runs = client1.app.state.runs

        response = client2.get(f"/run/{run_id}/exports/a-1")
        assert response.status_code == 403


# ── Create response read model ──────────────────────────────────────────────


class TestCreateResponseReadModel:
    def test_create_returns_read_model_response(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {"grade": 5},
            "teacher_id": "t-001",
        })
        data = response.json()
        assert "run_id" in data
        assert "status" in data
        assert "topic" in data
        assert "current_step" in data
        assert "artifact_types" in data

    def test_create_response_has_state(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        data = response.json()
        assert data["state"] is not None
        assert "raw_request" in data["state"]


class TestTeacherIdSpoofing:
    def test_create_uses_auth_user_not_request_teacher_id(self):
        teacher = _make_teacher(user_id="t-real", username="real")
        client = _make_app_with_auth(teacher)
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-spoofed",
        })
        run_id = response.json()["run_id"]
        app: FastAPI = client.app  # type: ignore[assignment]
        assert app.state.runs[run_id]["teacher_id"] == "t-real"

    def test_create_state_has_auth_user_id(self):
        teacher = _make_teacher(user_id="t-real", username="real")
        client = _make_app_with_auth(teacher)
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-spoofed",
        })
        data = response.json()
        assert data["state"]["teacher_id"] == "t-real"


# ── Status derivation (new statuses) ────────────────────────────────────────


_ARTIFACT_LESSON = {
    "artifact_type": "lesson",
    "title": "T",
    "sections": [{"content": "C"}],
}


class TestDeriveStatusNew:
    def test_generating_when_artifacts_present(self):
        state = {
            "blueprint_approved": True,
            "artifacts": [_ARTIFACT_LESSON],
        }
        assert _derive_status(state) == "generating"

    def test_generating_when_no_artifacts_yet(self):
        state = {"blueprint_approved": True, "artifacts": []}
        assert _derive_status(state) == "generating"

    def test_reviewing_when_judge_score_present(self):
        state = {
            "blueprint_approved": True,
            "judge_score": 8.0,
            "artifacts": [_ARTIFACT_LESSON],
        }
        assert _derive_status(state) == "reviewing"

    def test_export_ready_when_approved_no_files(self):
        state = {
            "teacher_approved": True,
            "artifacts": [_ARTIFACT_LESSON],
        }
        assert _derive_status(state) == "export_ready"

    def test_exporting_when_approved_with_files(self):
        state = {
            "teacher_approved": True,
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert _derive_status(state) == "exporting"

    def test_completed_when_export_ready_with_files(self):
        state = {
            "export_ready": True,
            "teacher_approved": True,
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert _derive_status(state) == "completed"
