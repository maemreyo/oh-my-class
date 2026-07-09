from __future__ import annotations

from services.gateway.teaching_session.models import SessionStatus
from services.gateway.teaching_session.status import (
    SessionTransitionAccepted,
    SessionTransitionRejected,
    validate_session_transition,
)


class TestTeachingSessionStatusMachine:
    def test_allows_scheduled_to_live(self) -> None:
        result = validate_session_transition(SessionStatus.SCHEDULED, SessionStatus.LIVE)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.SCHEDULED,
            to_status=SessionStatus.LIVE,
        )

    def test_allows_scheduled_to_expired(self) -> None:
        result = validate_session_transition(SessionStatus.SCHEDULED, SessionStatus.EXPIRED)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.SCHEDULED,
            to_status=SessionStatus.EXPIRED,
        )

    def test_allows_live_to_ended(self) -> None:
        result = validate_session_transition(SessionStatus.LIVE, SessionStatus.ENDED)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.LIVE,
            to_status=SessionStatus.ENDED,
        )

    def test_allows_ended_to_archived(self) -> None:
        result = validate_session_transition(SessionStatus.ENDED, SessionStatus.ARCHIVED)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.ENDED,
            to_status=SessionStatus.ARCHIVED,
        )

    def test_allows_ended_to_expired(self) -> None:
        result = validate_session_transition(SessionStatus.ENDED, SessionStatus.EXPIRED)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.ENDED,
            to_status=SessionStatus.EXPIRED,
        )

    def test_allows_archived_to_expired(self) -> None:
        result = validate_session_transition(SessionStatus.ARCHIVED, SessionStatus.EXPIRED)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.ARCHIVED,
            to_status=SessionStatus.EXPIRED,
        )

    def test_allows_idempotent_transition(self) -> None:
        result = validate_session_transition(SessionStatus.LIVE, SessionStatus.LIVE)

        assert result == SessionTransitionAccepted(
            from_status=SessionStatus.LIVE,
            to_status=SessionStatus.LIVE,
        )

    def test_rejects_scheduled_to_ended(self) -> None:
        result = validate_session_transition(SessionStatus.SCHEDULED, SessionStatus.ENDED)

        assert result == SessionTransitionRejected(
            from_status=SessionStatus.SCHEDULED,
            to_status=SessionStatus.ENDED,
            reason="transition_not_allowed",
        )

    def test_rejects_live_to_scheduled(self) -> None:
        result = validate_session_transition(SessionStatus.LIVE, SessionStatus.SCHEDULED)

        assert result == SessionTransitionRejected(
            from_status=SessionStatus.LIVE,
            to_status=SessionStatus.SCHEDULED,
            reason="transition_not_allowed",
        )

    def test_rejects_archived_to_live(self) -> None:
        result = validate_session_transition(SessionStatus.ARCHIVED, SessionStatus.LIVE)

        assert result == SessionTransitionRejected(
            from_status=SessionStatus.ARCHIVED,
            to_status=SessionStatus.LIVE,
            reason="transition_not_allowed",
        )

    def test_expired_is_terminal(self) -> None:
        for target in SessionStatus:
            if target is SessionStatus.EXPIRED:
                continue
            result = validate_session_transition(SessionStatus.EXPIRED, target)
            assert isinstance(result, SessionTransitionRejected)
