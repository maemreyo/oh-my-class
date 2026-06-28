from __future__ import annotations

from dataclasses import dataclass

from services.gateway.models import RunStatus


@dataclass(frozen=True, slots=True)
class StatusTransitionAccepted:
    from_status: RunStatus
    to_status: RunStatus


@dataclass(frozen=True, slots=True)
class StatusTransitionRejected:
    from_status: RunStatus
    to_status: RunStatus
    reason: str


type StatusTransitionResult = StatusTransitionAccepted | StatusTransitionRejected

_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.PENDING: frozenset({
        RunStatus.PLANNING,
        RunStatus.AWAITING_APPROVAL,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.PLANNING: frozenset({
        RunStatus.RESEARCHING,
        RunStatus.AWAITING_APPROVAL,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.RESEARCHING: frozenset({
        RunStatus.GENERATING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.GENERATING: frozenset({
        RunStatus.REVIEWING,
        RunStatus.AWAITING_APPROVAL,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.REVIEWING: frozenset({
        RunStatus.AWAITING_APPROVAL,
        RunStatus.EXPORTING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.AWAITING_APPROVAL: frozenset({
        RunStatus.PLANNING,
        RunStatus.GENERATING,
        RunStatus.EXPORTING,
        RunStatus.CANCELLED,
        RunStatus.FAILED,
    }),
    RunStatus.EXPORTING: frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}),
    RunStatus.COMPLETED: frozenset(),
    RunStatus.FAILED: frozenset(),
    RunStatus.CANCELLED: frozenset(),
}


def validate_status_transition(
    from_status: RunStatus,
    to_status: RunStatus,
) -> StatusTransitionResult:
    if from_status == to_status:
        return StatusTransitionAccepted(from_status=from_status, to_status=to_status)
    if to_status in _ALLOWED_TRANSITIONS[from_status]:
        return StatusTransitionAccepted(from_status=from_status, to_status=to_status)
    return StatusTransitionRejected(
        from_status=from_status,
        to_status=to_status,
        reason="transition_not_allowed",
    )
