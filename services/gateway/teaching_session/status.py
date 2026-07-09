"""TeachingSession lifecycle transition validation (TSP-01 AC1).

Mirrors the shape of `services/gateway/teaching_pack_status.py`'s RunStatus
transition table (same Accepted/Rejected result pattern) as an independent
implementation -- a TeachingSession is not a Run and has its own state shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.gateway.teaching_session.models import SessionStatus


@dataclass(frozen=True, slots=True)
class SessionTransitionAccepted:
    from_status: SessionStatus
    to_status: SessionStatus


@dataclass(frozen=True, slots=True)
class SessionTransitionRejected:
    from_status: SessionStatus
    to_status: SessionStatus
    reason: str


type SessionTransitionResult = SessionTransitionAccepted | SessionTransitionRejected

# scheduled -> live: teacher starts class.
# scheduled -> expired: the scheduled window lapsed without ever starting.
# live -> ended: teacher ends class (or a future recovery sweeper times it out
#   -- that sweeper is out of scope for this slice).
# ended -> archived: teacher/admin keeps it as a long-term, evidence-eligible
#   record.
# ended -> expired: retention window closes without an archive step.
# archived -> expired: retention window closes on an already-archived session.
# expired is terminal -- nothing resurrects an expired session.
_ALLOWED_TRANSITIONS: dict[SessionStatus, frozenset[SessionStatus]] = {
    SessionStatus.SCHEDULED: frozenset({SessionStatus.LIVE, SessionStatus.EXPIRED}),
    SessionStatus.LIVE: frozenset({SessionStatus.ENDED}),
    SessionStatus.ENDED: frozenset({SessionStatus.ARCHIVED, SessionStatus.EXPIRED}),
    SessionStatus.ARCHIVED: frozenset({SessionStatus.EXPIRED}),
    SessionStatus.EXPIRED: frozenset(),
}


def validate_session_transition(
    from_status: SessionStatus,
    to_status: SessionStatus,
) -> SessionTransitionResult:
    if from_status == to_status:
        return SessionTransitionAccepted(from_status=from_status, to_status=to_status)
    if to_status in _ALLOWED_TRANSITIONS[from_status]:
        return SessionTransitionAccepted(from_status=from_status, to_status=to_status)
    return SessionTransitionRejected(
        from_status=from_status,
        to_status=to_status,
        reason="transition_not_allowed",
    )
