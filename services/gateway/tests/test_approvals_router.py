from __future__ import annotations

from pydantic import ValidationError

from services.gateway.routers.approvals import (
    ApprovalAction,
    ApprovalRequest,
    ApprovalResponse,
)
from services.gateway.routers.runs import derive_status


class TestApprovalModels:
    def test_approval_request_requires_action(self) -> None:
        try:
            ApprovalRequest.model_validate({})
        except ValidationError as exc:
            assert "action" in str(exc)
        else:
            raise AssertionError("ApprovalRequest without action should fail validation")

    def test_approval_response_has_required_fields(self) -> None:
        response = ApprovalResponse(status="resumed", message="OK", run_id="r1")
        assert response.status == "resumed"
        assert response.run_id == "r1"


class TestApprovalActionEnum:
    def test_invalid_action_rejected(self) -> None:
        try:
            ApprovalRequest(action="maybe")
        except ValidationError as exc:
            assert "action" in str(exc)
        else:
            raise AssertionError("invalid action should fail validation")

    def test_approve_action_accepted(self) -> None:
        request = ApprovalRequest(action="approve")
        assert request.action == ApprovalAction.APPROVE

    def test_reject_action_accepted(self) -> None:
        request = ApprovalRequest(action="reject")
        assert request.action == ApprovalAction.REJECT


class TestDeriveStatus:
    def test_content_approval_gate_returns_awaiting_content_approval(self) -> None:
        state = {"gate_payload": {"gate": "content_approval"}, "artifacts": [{}]}
        assert derive_status(state) == "awaiting_content_approval"

    def test_blueprint_approval_gate_returns_awaiting_approval(self) -> None:
        state = {"gate_payload": {"gate": "blueprint_approval"}, "lesson_plan": {}}
        assert derive_status(state) == "awaiting_approval"

    def test_teacher_approved_returns_export_ready(self) -> None:
        state = {"teacher_approved": True, "lesson_plan": {}, "artifacts": [{}]}
        assert derive_status(state) == "export_ready"

    def test_teacher_approved_with_files_returns_exporting(self) -> None:
        state = {
            "teacher_approved": True,
            "lesson_plan": {},
            "artifacts": [{}],
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert derive_status(state) == "exporting"

    def test_export_ready_returns_completed(self) -> None:
        state = {
            "export_ready": True,
            "teacher_approved": True,
            "exported_files": [{"artifact_id": "a-1", "format": "html"}],
        }
        assert derive_status(state) == "completed"

    def test_error_returns_failed(self) -> None:
        assert derive_status({"error": "something broke"}) == "failed"

    def test_lesson_plan_without_gate_returns_awaiting_approval(self) -> None:
        assert derive_status({"lesson_plan": {"topic": "Math"}}) == "awaiting_approval"

    def test_empty_state_returns_running(self) -> None:
        assert derive_status({}) == "running"
