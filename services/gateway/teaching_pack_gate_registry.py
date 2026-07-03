from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never


class TeachingPackGateName(StrEnum):
    CLARIFICATION_REQUIRED = "clarification_required"
    CONTRACT_CONFIRMATION = "contract_confirmation"
    SEARCH_PLAN_CONFIRMATION = "search_plan_confirmation"
    BLUEPRINT_APPROVAL = "blueprint_approval"
    CONTENT_APPROVAL = "content_approval"
    UNIT_APPROVAL = "unit_approval"


class TeachingPackGateAction(StrEnum):
    ANSWER = "answer"
    APPROVE = "approve"
    APPROVE_SELECTED = "approve_selected"
    REJECT = "reject"
    REJECT_SELECTED = "reject_selected"
    EDIT = "edit"


@dataclass(frozen=True, slots=True)
class GateValidationAccepted:
    gate_name: TeachingPackGateName
    action: TeachingPackGateAction


@dataclass(frozen=True, slots=True)
class GateValidationRejected:
    reason: str


type GateValidationResult = GateValidationAccepted | GateValidationRejected


def validate_gate_response(gate_name: str, action: str) -> GateValidationResult:
    gate = _parse_gate_name(gate_name)
    if gate is None:
        return GateValidationRejected(reason="unknown_gate")
    parsed_action = _parse_gate_action(action)
    if parsed_action is None:
        return GateValidationRejected(reason="unknown_action")
    if parsed_action not in allowed_actions_for_gate(gate):
        return GateValidationRejected(reason="action_not_allowed")
    return GateValidationAccepted(gate_name=gate, action=parsed_action)


def allowed_actions_for_gate(gate: TeachingPackGateName) -> frozenset[TeachingPackGateAction]:
    match gate:
        case TeachingPackGateName.CLARIFICATION_REQUIRED:
            return frozenset({TeachingPackGateAction.ANSWER})
        case TeachingPackGateName.CONTRACT_CONFIRMATION:
            return frozenset({
                TeachingPackGateAction.APPROVE,
                TeachingPackGateAction.EDIT,
                TeachingPackGateAction.REJECT,
            })
        case TeachingPackGateName.SEARCH_PLAN_CONFIRMATION:
            return frozenset({TeachingPackGateAction.APPROVE, TeachingPackGateAction.EDIT})
        case TeachingPackGateName.BLUEPRINT_APPROVAL:
            return frozenset({
                TeachingPackGateAction.APPROVE,
                TeachingPackGateAction.REJECT,
                TeachingPackGateAction.EDIT,
            })
        case TeachingPackGateName.CONTENT_APPROVAL:
            return frozenset({
                TeachingPackGateAction.APPROVE,
                TeachingPackGateAction.APPROVE_SELECTED,
                TeachingPackGateAction.REJECT,
                TeachingPackGateAction.REJECT_SELECTED,
                TeachingPackGateAction.EDIT,
            })
        case TeachingPackGateName.UNIT_APPROVAL:
            return frozenset({
                TeachingPackGateAction.APPROVE,
                TeachingPackGateAction.REJECT,
                TeachingPackGateAction.EDIT,
            })
        case unreachable:
            assert_never(unreachable)


def _parse_gate_name(value: str) -> TeachingPackGateName | None:
    for gate in TeachingPackGateName:
        if gate.value == value:
            return gate
    return None


def _parse_gate_action(value: str) -> TeachingPackGateAction | None:
    for action in TeachingPackGateAction:
        if action.value == value:
            return action
    return None
