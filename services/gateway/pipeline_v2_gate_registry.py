from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never


class PipelineV2GateName(StrEnum):
    CLARIFICATION_REQUIRED = "clarification_required"
    CONTRACT_CONFIRMATION = "contract_confirmation"
    SEARCH_PLAN_CONFIRMATION = "search_plan_confirmation"
    BLUEPRINT_APPROVAL = "blueprint_approval"
    CONTENT_APPROVAL = "content_approval"


class PipelineV2GateAction(StrEnum):
    ANSWER = "answer"
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"


@dataclass(frozen=True, slots=True)
class GateValidationAccepted:
    gate_name: PipelineV2GateName
    action: PipelineV2GateAction


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


def allowed_actions_for_gate(gate: PipelineV2GateName) -> frozenset[PipelineV2GateAction]:
    match gate:
        case PipelineV2GateName.CLARIFICATION_REQUIRED:
            return frozenset({PipelineV2GateAction.ANSWER})
        case PipelineV2GateName.CONTRACT_CONFIRMATION:
            return frozenset({
                PipelineV2GateAction.APPROVE,
                PipelineV2GateAction.EDIT,
                PipelineV2GateAction.REJECT,
            })
        case PipelineV2GateName.SEARCH_PLAN_CONFIRMATION:
            return frozenset({PipelineV2GateAction.APPROVE, PipelineV2GateAction.EDIT})
        case PipelineV2GateName.BLUEPRINT_APPROVAL:
            return frozenset({
                PipelineV2GateAction.APPROVE,
                PipelineV2GateAction.REJECT,
                PipelineV2GateAction.EDIT,
            })
        case PipelineV2GateName.CONTENT_APPROVAL:
            return frozenset({
                PipelineV2GateAction.APPROVE,
                PipelineV2GateAction.REJECT,
                PipelineV2GateAction.EDIT,
            })
        case unreachable:
            assert_never(unreachable)


def _parse_gate_name(value: str) -> PipelineV2GateName | None:
    for gate in PipelineV2GateName:
        if gate.value == value:
            return gate
    return None


def _parse_gate_action(value: str) -> PipelineV2GateAction | None:
    for action in PipelineV2GateAction:
        if action.value == value:
            return action
    return None
