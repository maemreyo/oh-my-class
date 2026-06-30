"""Gate seam tests — validate_gate_response interrupt→resume transitions.

Tests use the real gate registry API: ``allowed_actions_for_gate`` and
``validate_gate_response``. All tests are deterministic — no LLM required.
"""
from __future__ import annotations

from services.gateway.teaching_pack_gate_registry import (
    GateValidationAccepted,
    GateValidationRejected,
    TeachingPackGateAction,
    TeachingPackGateName,
    allowed_actions_for_gate,
    validate_gate_response,
)


class TestAllGatesHaveValidActions:
    def test_every_gate_has_at_least_one_valid_action(self):
        """Every gate must have at least one valid action (non-empty frozenset)."""
        for gate in TeachingPackGateName:
            actions = allowed_actions_for_gate(gate)
            assert actions, f"Gate {gate.value!r} has no valid actions"

    def test_every_gate_action_is_valid_enum_member(self):
        """Every action in every gate's set must be a TeachingPackGateAction."""
        for gate in TeachingPackGateName:
            for action in allowed_actions_for_gate(gate):
                assert isinstance(action, TeachingPackGateAction), (
                    f"Gate {gate.value!r} has non-TeachingPackGateAction action: {action!r}"
                )


class TestClarificationRequiredGate:
    def test_answer_is_allowed(self):
        result = validate_gate_response("clarification_required", "answer")
        assert isinstance(result, GateValidationAccepted)
        assert result.action == TeachingPackGateAction.ANSWER

    def test_approve_is_not_allowed(self):
        result = validate_gate_response("clarification_required", "approve")
        assert isinstance(result, GateValidationRejected)
        assert result.reason == "action_not_allowed"


class TestContractConfirmationGate:
    def test_approve_is_allowed(self):
        result = validate_gate_response("contract_confirmation", "approve")
        assert isinstance(result, GateValidationAccepted)

    def test_edit_is_allowed(self):
        result = validate_gate_response("contract_confirmation", "edit")
        assert isinstance(result, GateValidationAccepted)

    def test_reject_is_allowed(self):
        result = validate_gate_response("contract_confirmation", "reject")
        assert isinstance(result, GateValidationAccepted)

    def test_answer_is_not_allowed(self):
        result = validate_gate_response("contract_confirmation", "answer")
        assert isinstance(result, GateValidationRejected)


class TestSearchPlanConfirmationGate:
    def test_approve_is_allowed(self):
        result = validate_gate_response("search_plan_confirmation", "approve")
        assert isinstance(result, GateValidationAccepted)

    def test_edit_is_allowed(self):
        result = validate_gate_response("search_plan_confirmation", "edit")
        assert isinstance(result, GateValidationAccepted)

    def test_reject_is_not_allowed(self):
        """search_plan_confirmation does not allow outright rejection."""
        result = validate_gate_response("search_plan_confirmation", "reject")
        assert isinstance(result, GateValidationRejected)


class TestBlueprintApprovalGate:
    def test_approve_is_allowed(self):
        result = validate_gate_response("blueprint_approval", "approve")
        assert isinstance(result, GateValidationAccepted)

    def test_reject_is_allowed(self):
        result = validate_gate_response("blueprint_approval", "reject")
        assert isinstance(result, GateValidationAccepted)

    def test_edit_is_allowed(self):
        result = validate_gate_response("blueprint_approval", "edit")
        assert isinstance(result, GateValidationAccepted)


class TestContentApprovalGate:
    def test_approve_is_allowed(self):
        result = validate_gate_response("content_approval", "approve")
        assert isinstance(result, GateValidationAccepted)

    def test_reject_is_allowed(self):
        result = validate_gate_response("content_approval", "reject")
        assert isinstance(result, GateValidationAccepted)

    def test_edit_is_allowed(self):
        result = validate_gate_response("content_approval", "edit")
        assert isinstance(result, GateValidationAccepted)


class TestUnknownGateAndAction:
    def test_unknown_gate_is_rejected(self):
        result = validate_gate_response("nonexistent_gate", "approve")
        assert isinstance(result, GateValidationRejected)
        assert result.reason == "unknown_gate"

    def test_unknown_action_is_rejected(self):
        result = validate_gate_response("contract_confirmation", "not_an_action")
        assert isinstance(result, GateValidationRejected)
        assert result.reason == "unknown_action"
