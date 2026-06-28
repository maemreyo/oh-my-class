"""Tests for approvals_router — approve and reject endpoints."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# jwt is not installed in the test environment — inject before gateway imports
if "jwt" not in sys.modules:
    sys.modules["jwt"] = MagicMock()

from packages.agents.events import (  # noqa: E402
    _event_store,
    _event_subscribers,
)
from services.gateway.auth.models import Role, User  # noqa: E402
from services.gateway.middleware.error_handler import register_exception_handlers  # noqa: E402
from services.gateway.routers.approvals import (  # noqa: E402
    ApprovalRequest,
    ApprovalResponse,
    router,
)
from services.gateway.routers.runs import (  # noqa: E402
    _derive_status,
)

# ── helpers ───────────────────────────────────────────────────────────────────

GATE_PAYLOAD = {
    "gate": "blueprint_approval",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "run_id": "test-run-123",
}

GATE_PAYLOAD_WITH_FEEDBACK = {
    "gate": "blueprint_approval",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "run_id": "test-run-123",
    "action": "reject",
    "feedback": "Needs more examples",
}

APPROVED_STATE: dict[str, Any] = {
    "raw_request": "Teach photosynthesis",
    "teacher_id": "t-001",
    "class_info": {"grade": 5},
    "run_id": "test-run-123",
    "blueprint_approved": False,
    "teacher_decision": "approve",
    "revision_feedback": "",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "research_policy": "standard",
    "artifact_types": [],
    "theme": "default",
    "artifacts": [],
    "quality_passed": False,
    "teacher_approved": False,
    "revision_count": 0,
    "export_formats": ["html"],
    "exported_files": [],
    "current_step": 5,
    "tokens_used": 0,
    "cost_usd": 0.0,
}

REJECTED_STATE: dict[str, Any] = {
    "raw_request": "Teach photosynthesis",
    "teacher_id": "t-001",
    "class_info": {"grade": 5},
    "run_id": "test-run-123",
    "blueprint_approved": False,
    "teacher_decision": "reject",
    "revision_feedback": "Needs more examples",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "research_policy": "standard",
    "artifact_types": [],
    "theme": "default",
    "artifacts": [],
    "quality_passed": False,
    "teacher_approved": False,
    "revision_count": 1,
    "gate_payload": GATE_PAYLOAD,  # gate_01 fires again after reject
    "export_formats": ["html"],
    "exported_files": [],
    "current_step": 4,
    "tokens_used": 0,
    "cost_usd": 0.0,
}


@pytest.fixture(autouse=True)
def _clear_event_store():
    _event_store.clear()
    _event_subscribers.clear()
    yield
    _event_store.clear()
    _event_subscribers.clear()


def _make_teacher() -> User:
    return User(user_id="t-001", username="teacher1", role=Role.TEACHER)


def _make_mock_graph(return_state: dict[str, Any] | None = None) -> MagicMock:
    """Build a mock graph whose ainvoke returns *return_state*."""
    state = return_state or APPROVED_STATE
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value=dict(state))
    return graph


def _seed_run(
    runs: dict[str, Any],
    run_id: str = "test-run-123",
    status: str = "awaiting_approval",
    state: dict[str, Any] | None = None,
) -> None:
    """Insert a run into the in-memory store with a gate_payload."""
    state_keys_to_keep = ("teacher_decision", "revision_feedback")
    runs[run_id] = {
        "run_id": run_id,
        "status": status,
        "state": state or {
            **{k: v for k, v in APPROVED_STATE.items() if k not in state_keys_to_keep},
            "gate_payload": GATE_PAYLOAD,
        },
        "teacher_id": "t-001",
        "created_at": "2026-01-01T00:00:00Z",
    }


def _make_app(
    graph: MagicMock | None = None,
    runs: dict[str, Any] | None = None,
) -> TestClient:
    """Build a minimal FastAPI app with auth, error handlers, and state."""
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)

    app.state.graph = graph or _make_mock_graph()
    app.state.runs = runs if runs is not None else {}

    teacher = _make_teacher()
    app.dependency_overrides[require_teacher] = lambda: teacher
    return TestClient(app)


def _make_app_no_auth() -> TestClient:
    """Build a minimal FastAPI app WITHOUT auth override."""
    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)
    app.state.graph = _make_mock_graph()
    app.state.runs = {}
    return TestClient(app)


# ── Approve endpoint ──────────────────────────────────────────────────────────

class TestApproveEndpoint:
    def test_approve_returns_200(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 200

    def test_approve_returns_approval_response(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        data = response.json()
        assert data["status"] == "resumed"
        assert data["run_id"] == "test-run-123"
        assert "message" in data

    def test_approve_requires_auth(self):
        client = _make_app_no_auth()
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "approve"},
        )
        assert response.status_code in (401, 403, 422)

    def test_approve_accepts_optional_feedback(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "approve", "feedback": "Looks good"},
        )
        assert response.status_code == 200

    def test_approve_not_found_returns_404(self):
        client = _make_app()
        response = client.post("/run/nonexistent/approve", json={"action": "approve"})
        assert response.status_code == 404

    def test_approve_not_at_gate_returns_error(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        # Remove gate_payload so run is not at a gate
        runs["test-run-123"]["state"]["gate_payload"] = None
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 422

    def test_approve_wrong_gate_returns_error(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        # Set gate_payload to a gate that is not an approval gate
        runs["test-run-123"]["state"]["gate_payload"] = {
            "gate": "some_other_gate",
            "data": [],
        }
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 422

    def test_approve_updates_run_status(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        client.post("/run/test-run-123/approve", json={"action": "approve"})
        # _derive_status sees lesson_plan in APPROVED_STATE → "awaiting_approval"
        assert runs["test-run-123"]["status"] == "awaiting_approval"

    def test_approve_updates_run_state(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert runs["test-run-123"]["state"]["teacher_decision"] == "approve"

    def test_approve_emits_gate_approved_event(self):
        runs: dict[str, Any] = {}
        _seed_run(runs, run_id="evt-run")
        client = _make_app(runs=runs)
        client.post("/run/evt-run/approve", json={"action": "approve"})
        events = _event_store.get("evt-run", [])
        gate_events = [e for e in events if e["event_type"] == "gate_approved"]
        assert len(gate_events) == 1
        assert gate_events[0]["gate"] == "blueprint_approval"

    def test_approve_graph_failure_returns_500(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        failing_graph = MagicMock()
        failing_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        client = _make_app(graph=failing_graph, runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 500


# ── Reject endpoint ───────────────────────────────────────────────────────────

class TestRejectEndpoint:
    def test_reject_with_feedback_returns_200(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        assert response.status_code == 200

    def test_reject_returns_approval_response(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Too long"},
        )
        data = response.json()
        assert data["status"] == "resumed"
        assert data["run_id"] == "test-run-123"

    def test_reject_without_feedback_returns_400(self):
        client = _make_app()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject"},
        )
        assert response.status_code == 400
        body = response.json()
        assert "feedback" in body.get("message", body.get("detail", "")).lower()

    def test_reject_with_empty_feedback_returns_400(self):
        client = _make_app()
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

    def test_reject_not_found_returns_404(self):
        client = _make_app()
        response = client.post(
            "/run/nonexistent/reject",
            json={"action": "reject", "feedback": "bad"},
        )
        assert response.status_code == 404

    def test_reject_not_at_gate_returns_error(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        runs["test-run-123"]["state"]["gate_payload"] = None
        client = _make_app(runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "bad"},
        )
        assert response.status_code == 422

    def test_reject_records_feedback_in_state(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        state = runs["test-run-123"]["state"]
        assert state["revision_feedback"] == "Needs more examples"
        assert state["teacher_decision"] == "reject"

    def test_reject_increments_revision_count(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        assert runs["test-run-123"]["state"]["revision_count"] == 1

    def test_reject_emits_gate_rejected_event(self):
        runs: dict[str, Any] = {}
        _seed_run(runs, run_id="evt-reject")
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post(
            "/run/evt-reject/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        events = _event_store.get("evt-reject", [])
        gate_events = [e for e in events if e["event_type"] == "gate_rejected"]
        assert len(gate_events) == 1
        assert gate_events[0]["gate"] == "blueprint_approval"
        assert gate_events[0]["feedback"] == "Needs more examples"

    def test_reject_graph_failure_returns_500(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        failing_graph = MagicMock()
        failing_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
        client = _make_app(graph=failing_graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "bad"},
        )
        assert response.status_code == 500


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


# ── Content approval (Gate 2) ──────────────────────────────────────────────

CONTENT_GATE_PAYLOAD = {
    "gate": "content_approval",
    "artifacts": [{"artifact_id": "a-1", "type": "worksheet", "title": "Worksheet 1"}],
    "review_results": {"overall_score": 8.5},
    "run_id": "test-run-123",
}

CONTENT_APPROVED_STATE: dict[str, Any] = {
    "raw_request": "Teach photosynthesis",
    "teacher_id": "t-001",
    "class_info": {"grade": 5},
    "run_id": "test-run-123",
    "blueprint_approved": False,
    "teacher_decision": "approve",
    "revision_feedback": "",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "research_policy": "standard",
    "artifact_types": ["worksheet", "quiz"],
    "theme": "default",
    "artifacts": [{"artifact_id": "a-1", "type": "worksheet", "title": "Worksheet 1"}],
    "quality_scores": {"overall": 8.5},
    "quality_passed": True,
    "teacher_approved": True,
    "revision_count": 0,
    "export_formats": ["html"],
    "exported_files": [],
    "current_step": 12,
    "tokens_used": 0,
    "cost_usd": 0.0,
}

CONTENT_REJECTED_STATE: dict[str, Any] = {
    "raw_request": "Teach photosynthesis",
    "teacher_id": "t-001",
    "class_info": {"grade": 5},
    "run_id": "test-run-123",
    "blueprint_approved": False,
    "teacher_decision": "reject",
    "revision_feedback": "Artifacts need more visual elements",
    "lesson_plan": {"topic": "Photosynthesis", "grade_level": "Grade 5"},
    "research_policy": "standard",
    "artifact_types": ["worksheet", "quiz"],
    "theme": "default",
    "artifacts": [{"artifact_id": "a-1", "type": "worksheet", "title": "Worksheet 1"}],
    "quality_scores": {"overall": 8.5},
    "quality_passed": True,
    "teacher_approved": False,
    "revision_count": 2,
    "gate_payload": CONTENT_GATE_PAYLOAD,
    "export_formats": ["html"],
    "exported_files": [],
    "current_step": 8,
    "tokens_used": 0,
    "cost_usd": 0.0,
}


def _seed_content_run(
    runs: dict[str, Any],
    run_id: str = "test-run-123",
    status: str = "awaiting_content_approval",
) -> None:
    """Insert a run at the content_approval gate into the in-memory store."""
    runs[run_id] = {
        "run_id": run_id,
        "status": status,
        "state": {
            k: v
            for k, v in CONTENT_APPROVED_STATE.items()
            if k not in ("teacher_decision", "revision_feedback", "teacher_approved")
        }
        | {"gate_payload": CONTENT_GATE_PAYLOAD},
        "teacher_id": "t-001",
        "created_at": "2026-01-01T00:00:00Z",
    }


class TestContentApproval:
    def test_approve_content_gate_returns_200(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 200

    def test_approve_content_gate_returns_content_message(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        data = response.json()
        assert data["status"] == "resumed"
        assert "content approved" in data["message"]

    def test_approve_content_gate_advances_status(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        graph = _make_mock_graph(CONTENT_APPROVED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert runs["test-run-123"]["status"] in ("export_ready", "exporting")

    def test_approve_content_gate_emits_correct_event(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs, run_id="c-approve")
        client = _make_app(runs=runs)
        client.post("/run/c-approve/approve", json={"action": "approve"})
        events = _event_store.get("c-approve", [])
        gate_events = [e for e in events if e["event_type"] == "gate_approved"]
        assert len(gate_events) == 1
        assert gate_events[0]["gate"] == "content_approval"

    def test_reject_content_gate_requires_feedback(self):
        client = _make_app()
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject"},
        )
        assert response.status_code == 400

    def test_reject_content_gate_with_feedback_returns_200(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        graph = _make_mock_graph(CONTENT_REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more visual elements"},
        )
        assert response.status_code == 200

    def test_reject_content_gate_returns_content_message(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        graph = _make_mock_graph(CONTENT_REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more visual elements"},
        )
        data = response.json()
        assert data["status"] == "resumed"
        assert "content rejected" in data["message"]

    def test_reject_content_gate_emits_correct_event(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs, run_id="c-reject")
        graph = _make_mock_graph(CONTENT_REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post(
            "/run/c-reject/reject",
            json={"action": "reject", "feedback": "Needs more visual elements"},
        )
        events = _event_store.get("c-reject", [])
        gate_events = [e for e in events if e["event_type"] == "gate_rejected"]
        assert len(gate_events) == 1
        assert gate_events[0]["gate"] == "content_approval"
        assert gate_events[0]["feedback"] == "Needs more visual elements"

    def test_reject_content_gate_loops_to_generate(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        graph = _make_mock_graph(CONTENT_REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Artifacts need more visual elements"},
        )
        state = runs["test-run-123"]["state"]
        assert state["teacher_decision"] == "reject"
        assert state["revision_feedback"] == "Artifacts need more visual elements"

    def test_wrong_gate_returns_error(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        runs["test-run-123"]["state"]["gate_payload"] = {
            "gate": "some_other_gate",
        }
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 422

    def test_no_gate_payload_returns_error(self):
        runs: dict[str, Any] = {}
        _seed_content_run(runs)
        runs["test-run-123"]["state"]["gate_payload"] = None
        client = _make_app(runs=runs)
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 422


# ── Ownership guard ─────────────────────────────────────────────────────────


def _make_teacher2() -> User:
    return User(user_id="t-002", username="teacher2", role=Role.TEACHER)


def _make_admin_user() -> User:
    return User(user_id="admin-001", username="admin1", role=Role.ADMIN)


def _make_app_with_user(user: User) -> TestClient:
    from services.gateway.auth.dependencies import require_teacher

    app = FastAPI()
    app.include_router(router, prefix="/run")
    register_exception_handlers(app)
    app.state.graph = _make_mock_graph()
    app.state.runs = {}
    app.dependency_overrides[require_teacher] = lambda: user
    return TestClient(app)


class TestOwnershipGuard:
    def test_approve_denied_for_other_teacher(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)

        teacher2_client = _make_app_with_user(_make_teacher2())
        teacher2_client.app.state.runs = runs

        response = teacher2_client.post(
            "/run/test-run-123/approve",
            json={"action": "approve"},
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "AUTHORIZATION_ERROR"

    def test_reject_denied_for_other_teacher(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)

        teacher2_client = _make_app_with_user(_make_teacher2())
        teacher2_client.app.state.runs = runs

        response = teacher2_client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "bad"},
        )
        assert response.status_code == 403

    def test_approve_allowed_for_admin(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)

        admin_client = _make_app_with_user(_make_admin_user())
        admin_client.app.state.runs = runs

        response = admin_client.post(
            "/run/test-run-123/approve",
            json={"action": "approve"},
        )
        assert response.status_code == 200


# ── ApprovalRequest action enum ─────────────────────────────────────────────


class TestApprovalActionEnum:
    def test_invalid_action_rejected(self):
        from pydantic import ValidationError as PydanticValidationError

        with pytest.raises(PydanticValidationError):
            ApprovalRequest(action="invalid_action")

    def test_approve_action_accepted(self):
        req = ApprovalRequest(action="approve")
        assert req.action == "approve"

    def test_reject_action_accepted(self):
        req = ApprovalRequest(action="reject")
        assert req.action == "reject"


class TestActionEndpointConsistency:
    def test_approve_endpoint_rejects_wrong_action(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "reject", "feedback": "bad"},
        )
        assert response.status_code == 422

    def test_reject_endpoint_rejects_wrong_action(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "approve"},
        )
        assert response.status_code == 422

    def test_approve_endpoint_accepts_correct_action(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        client = _make_app(runs=runs)
        response = client.post(
            "/run/test-run-123/approve",
            json={"action": "approve"},
        )
        assert response.status_code == 200

    def test_reject_endpoint_accepts_correct_action(self):
        runs: dict[str, Any] = {}
        _seed_run(runs)
        graph = _make_mock_graph(REJECTED_STATE)
        client = _make_app(graph=graph, runs=runs)
        response = client.post(
            "/run/test-run-123/reject",
            json={"action": "reject", "feedback": "Needs more examples"},
        )
        assert response.status_code == 200


class TestDeriveStatus:
    def test_content_approval_gate_returns_awaiting_content_approval(self):
        state = {"gate_payload": {"gate": "content_approval"}, "artifacts": [{}]}
        assert _derive_status(state) == "awaiting_content_approval"

    def test_blueprint_approval_gate_returns_awaiting_approval(self):
        state = {"gate_payload": {"gate": "blueprint_approval"}, "lesson_plan": {}}
        assert _derive_status(state) == "awaiting_approval"

    def test_teacher_approved_returns_export_ready(self):
        state = {"teacher_approved": True, "lesson_plan": {}, "artifacts": [{}]}
        assert _derive_status(state) == "export_ready"

    def test_teacher_approved_with_files_returns_exporting(self):
        state = {
            "teacher_approved": True,
            "lesson_plan": {},
            "artifacts": [{}],
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert _derive_status(state) == "exporting"

    def test_export_ready_returns_completed(self):
        state = {
            "export_ready": True,
            "teacher_approved": True,
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert _derive_status(state) == "completed"

    def test_error_returns_failed(self):
        state = {"error": "something broke"}
        assert _derive_status(state) == "failed"

    def test_lesson_plan_without_gate_returns_awaiting_approval(self):
        state = {"lesson_plan": {"topic": "Math"}}
        assert _derive_status(state) == "awaiting_approval"

    def test_empty_state_returns_running(self):
        assert _derive_status({}) == "running"
