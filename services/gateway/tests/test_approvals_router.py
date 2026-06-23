"""Tests for approvals_router — approve and reject endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

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
from services.gateway.routers.approvals import (  # noqa: E402
    ApprovalRequest,
    ApprovalResponse,
    router,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_teacher() -> User:
    return User(user_id="t-001", username="teacher1", role=Role.TEACHER)


def _make_app_with_auth_override() -> TestClient:
    """Build a minimal FastAPI app with auth dependency overridden."""
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")

    teacher = _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


def _make_app_no_auth() -> TestClient:
    """Build a minimal FastAPI app WITHOUT auth override (uses real JWT)."""
    app = FastAPI()
    app.include_router(router, prefix="/run")
    return TestClient(app)


# ── Approve endpoint ──────────────────────────────────────────────────────────

class TestApproveEndpoint:
    def test_approve_returns_200(self):
        client = _make_app_with_auth_override()
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 200

    def test_approve_returns_approval_response(self):
        client = _make_app_with_auth_override()
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        data = response.json()
        assert data["status"] == "resumed"
        assert data["run_id"] == "test-run-123"
        assert "message" in data

    def test_approve_requires_auth(self):
        client = _make_app_no_auth()
        # No Authorization header → 403 (HTTPBearer rejects missing header)
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "approve"},
        )
        assert response.status_code in (401, 403, 422)

    def test_approve_accepts_optional_feedback(self):
        client = _make_app_with_auth_override()
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "approve", "feedback": "Looks good"},
        )
        assert response.status_code == 200


# ── Reject endpoint ───────────────────────────────────────────────────────────

class TestRejectEndpoint:
    def test_reject_with_feedback_returns_200(self):
        client = _make_app_with_auth_override()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        assert response.status_code == 200

    def test_reject_returns_approval_response(self):
        client = _make_app_with_auth_override()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Too long"},
        )
        data = response.json()
        assert data["status"] == "resumed"
        assert data["run_id"] == "test-run-123"

    def test_reject_without_feedback_returns_400(self):
        client = _make_app_with_auth_override()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject"},
        )
        assert response.status_code == 400
        assert "feedback" in response.json()["detail"].lower()

    def test_reject_with_empty_feedback_returns_400(self):
        client = _make_app_with_auth_override()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": ""},
        )
        assert response.status_code == 400

    def test_reject_requires_auth(self):
        client = _make_app_no_auth()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "text"},
        )
        assert response.status_code in (401, 403, 422)


# ── ApprovalRequest / ApprovalResponse models ─────────────────────────────────

class TestApprovalModels:
    def test_approval_request_requires_action(self):
        req = ApprovalRequest(action="approve")
        assert req.action == "approve"
        assert req.feedback is None

    def test_approval_response_has_required_fields(self):
        resp = ApprovalResponse(status="resumed", message="done", run_id="r-1")
        assert resp.status == "resumed"
        assert resp.run_id == "r-1"
