"""Tests for runs_router — create, get, and SSE stream endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# jwt is not installed in the test environment — inject before gateway imports
if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.routers.runs import RunRequest, RunResponse, router  # noqa: E402

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_teacher() -> User:
    return User(user_id="t-001", username="teacher1", role=Role.TEACHER)


def _make_app_with_auth() -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")

    teacher = _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


def _make_app_no_auth() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/run")
    return TestClient(app)


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

    def test_create_run_returns_created_status(self):
        client = _make_app_with_auth()
        response = client.post("/run", json={
            "raw_request": "Teach science",
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.json()["status"] == "created"

    def test_create_run_generates_unique_ids(self):
        client = _make_app_with_auth()
        payload = {"raw_request": "Teach X", "class_info": {}, "teacher_id": "t-001"}
        r1 = client.post("/run", json=payload)
        r2 = client.post("/run", json=payload)
        assert r1.json()["run_id"] != r2.json()["run_id"]

    def test_create_run_requires_auth(self):
        client = _make_app_no_auth()
        response = client.post("/run", json={
            "raw_request": "Teach X",
            "class_info": {},
            "teacher_id": "t-001",
        })
        assert response.status_code in (401, 403, 422)


# ── get_run ───────────────────────────────────────────────────────────────────

class TestGetRun:
    def test_get_run_returns_200(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123")
        assert response.status_code == 200

    def test_get_run_returns_run_id(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123")
        assert response.json()["run_id"] == "test-run-123"

    def test_get_run_returns_state(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123")
        data = response.json()
        assert "status" in data

    def test_get_run_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/test-run-123")
        assert response.status_code in (401, 403, 422)


# ── get_run_status (SSE) ──────────────────────────────────────────────────────

class TestGetRunStatus:
    def test_sse_returns_200(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123/status")
        assert response.status_code == 200

    def test_sse_content_type_is_event_stream(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123/status")
        assert "text/event-stream" in response.headers["content-type"]

    def test_sse_has_cache_control_header(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123/status")
        assert response.headers.get("cache-control") == "no-cache"

    def test_sse_body_contains_step_start(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123/status")
        assert "step_start" in response.text

    def test_sse_body_contains_complete(self):
        client = _make_app_with_auth()
        response = client.get("/run/test-run-123/status")
        assert "complete" in response.text

    def test_sse_requires_auth(self):
        client = _make_app_no_auth()
        response = client.get("/run/test-run-123/status")
        assert response.status_code in (401, 403, 422)


# ── RunRequest / RunResponse models ──────────────────────────────────────────

class TestRunModels:
    def test_run_request_has_required_fields(self):
        req = RunRequest(raw_request="Teach X", class_info={}, teacher_id="t-001")
        assert req.teacher_id == "t-001"

    def test_run_response_has_required_fields(self):
        resp = RunResponse(run_id="r-1", status="created")
        assert resp.run_id == "r-1"
        assert resp.state is None
