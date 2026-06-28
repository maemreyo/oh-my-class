from __future__ import annotations

from services.gateway.teaching_pack_gate_registry import (
    GateValidationAccepted,
    GateValidationRejected,
    TeachingPackGateAction,
    TeachingPackGateName,
    allowed_actions_for_gate,
    validate_gate_response,
)


class TestTeachingPackGateRegistry:
    def test_allows_blueprint_approval_actions(self) -> None:
        result = validate_gate_response("blueprint_approval", "approve")

        assert result == GateValidationAccepted(
            gate_name=TeachingPackGateName.BLUEPRINT_APPROVAL,
            action=TeachingPackGateAction.APPROVE,
        )

    def test_rejects_unknown_gate(self) -> None:
        result = validate_gate_response("unknown_gate", "approve")

        assert result == GateValidationRejected(reason="unknown_gate")

    def test_rejects_unknown_action(self) -> None:
        result = validate_gate_response("blueprint_approval", "maybe")

        assert result == GateValidationRejected(reason="unknown_action")

    def test_rejects_action_not_allowed_for_clarification(self) -> None:
        result = validate_gate_response("clarification_required", "approve")

        assert result == GateValidationRejected(reason="action_not_allowed")

    def test_clarification_only_accepts_answer(self) -> None:
        actions = allowed_actions_for_gate(TeachingPackGateName.CLARIFICATION_REQUIRED)

        assert actions == frozenset({TeachingPackGateAction.ANSWER})

    def test_contract_confirmation_accepts_cancel_reject_path(self) -> None:
        result = validate_gate_response("contract_confirmation", "reject")

        assert result == GateValidationAccepted(
            gate_name=TeachingPackGateName.CONTRACT_CONFIRMATION,
            action=TeachingPackGateAction.REJECT,
        )


def test_all_issue_003_gate_names_are_registered() -> None:
    assert {gate.value for gate in TeachingPackGateName} == {
        "clarification_required",
        "contract_confirmation",
        "search_plan_confirmation",
        "blueprint_approval",
        "content_approval",
    }
