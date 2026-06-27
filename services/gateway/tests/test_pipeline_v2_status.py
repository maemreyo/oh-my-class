from __future__ import annotations

from services.gateway.models import RunStatus
from services.gateway.pipeline_v2_status import (
    StatusTransitionAccepted,
    StatusTransitionRejected,
    validate_status_transition,
)


class TestPipelineV2StatusMachine:
    def test_allows_pending_to_planning(self) -> None:
        result = validate_status_transition(RunStatus.PENDING, RunStatus.PLANNING)

        assert result == StatusTransitionAccepted(
            from_status=RunStatus.PENDING,
            to_status=RunStatus.PLANNING,
        )

    def test_allows_idempotent_transition(self) -> None:
        result = validate_status_transition(RunStatus.PLANNING, RunStatus.PLANNING)

        assert result == StatusTransitionAccepted(
            from_status=RunStatus.PLANNING,
            to_status=RunStatus.PLANNING,
        )

    def test_rejects_completed_to_generating(self) -> None:
        result = validate_status_transition(RunStatus.COMPLETED, RunStatus.GENERATING)

        assert result == StatusTransitionRejected(
            from_status=RunStatus.COMPLETED,
            to_status=RunStatus.GENERATING,
            reason="transition_not_allowed",
        )

    def test_rejects_pending_to_completed(self) -> None:
        result = validate_status_transition(RunStatus.PENDING, RunStatus.COMPLETED)

        assert result == StatusTransitionRejected(
            from_status=RunStatus.PENDING,
            to_status=RunStatus.COMPLETED,
            reason="transition_not_allowed",
        )
