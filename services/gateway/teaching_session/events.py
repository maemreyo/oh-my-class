"""TeachingSession significant-event types and the derived read-model reducer (TSP-03).

Every live session action is one of seven significant event types (base AC1).
Events are immutable, validated-at-construction Pydantic models; the *current*
teacher/display/student UI state is never stored directly -- it is *derived*
by folding events through `apply_event` (base AC2), which is the one place
that knows how each event type changes state. `apply_event` is deliberately
last-write-wins per field (not accumulating deltas), which matters for
recovery: replaying the same event twice (e.g. because Redis-hot state was
missing and Postgres recovery re-derives from events that already include the
newest one) is a safe no-op, not a double-count. See `event_log.py` for the
Postgres-backed store and Redis-hot state that use these types, and
`live_sync.py` for the Redis Pub/Sub transport.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime  # noqa: TC003
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from services.gateway.models import utc_now
from services.gateway.teaching_session.tokens import SessionRole  # noqa: TC001


class SessionEventType(StrEnum):
    """The significant TeachingSession event types (base AC1)."""

    SESSION_STARTED = "session_started"
    SLIDE_CHANGED = "slide_changed"
    INTERACTION_OPENED = "interaction_opened"
    AGGREGATE_UPDATED = "aggregate_updated"
    BRANCH_SELECTED = "branch_selected"
    ANNOTATION_ADDED = "annotation_added"
    SESSION_ENDED = "session_ended"


# ---------------------------------------------------------------------------
# Per-type payloads -- what `apply_event` reads and what a caller must supply.
# ---------------------------------------------------------------------------


class SessionStartedPayload(BaseModel):
    deck_id: str
    snapshot_id: str


class SlideChangedPayload(BaseModel):
    slide_id: str
    slide_index: int | None = None


class InteractionOpenedPayload(BaseModel):
    interaction_id: str
    slide_id: str
    interaction_kind: str | None = None


class AggregateUpdatedPayload(BaseModel):
    """`tallies` is the *full current* aggregate snapshot for `interaction_id`,
    not a delta -- the caller (student-response route) is responsible for
    computing the updated snapshot; this event just records it."""

    interaction_id: str
    tallies: dict[str, int]


class BranchSelectedPayload(BaseModel):
    slide_id: str
    branch_id: str


class AnnotationAddedPayload(BaseModel):
    slide_id: str
    annotation_id: str
    annotation_kind: str | None = None


class SessionEndedPayload(BaseModel):
    reason: str | None = None


_PAYLOAD_MODELS: dict[SessionEventType, type[BaseModel]] = {
    SessionEventType.SESSION_STARTED: SessionStartedPayload,
    SessionEventType.SLIDE_CHANGED: SlideChangedPayload,
    SessionEventType.INTERACTION_OPENED: InteractionOpenedPayload,
    SessionEventType.AGGREGATE_UPDATED: AggregateUpdatedPayload,
    SessionEventType.BRANCH_SELECTED: BranchSelectedPayload,
    SessionEventType.ANNOTATION_ADDED: AnnotationAddedPayload,
    SessionEventType.SESSION_ENDED: SessionEndedPayload,
}


class SessionEvent(BaseModel):
    """An immutable, persisted-or-about-to-be-persisted significant event.

    `sequence` is `None` until `event_log.append_event` assigns the
    per-session monotonic value (base AC5 "event resume via last event ID").
    """

    event_id: str
    session_id: str
    event_type: SessionEventType
    actor_role: SessionRole
    payload: dict[str, Any]
    created_at: datetime
    sequence: int | None = None


def build_event(
    *,
    session_id: str,
    event_type: SessionEventType,
    actor_role: SessionRole,
    payload: dict[str, Any] | BaseModel,
    event_id: str | None = None,
    created_at: datetime | None = None,
) -> SessionEvent:
    """Validate `payload` against `event_type`'s payload model, then build the event.

    Raises `pydantic.ValidationError` if `payload` doesn't match the shape
    `event_type` requires -- this is what makes the event log typed rather
    than an unstructured JSON grab-bag.
    """
    payload_model = _PAYLOAD_MODELS[event_type]
    raw_payload = payload.model_dump() if isinstance(payload, BaseModel) else payload
    validated = payload_model.model_validate(raw_payload)
    return SessionEvent(
        event_id=event_id or f"evt-{uuid4()}",
        session_id=session_id,
        event_type=event_type,
        actor_role=actor_role,
        payload=validated.model_dump(mode="json"),
        created_at=created_at or utc_now(),
    )


# ---------------------------------------------------------------------------
# Derived read model -- fast teacher/display/student UI state (base AC2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionReadModel:
    """The current derived state of a live session.

    This is what's Redis-hot (TSP-03 amendment) and what `event_log.
    recover_read_model` rebuilds by replaying the last N Postgres events on a
    Redis miss. Roster/participant-count tracking is deliberately out of
    scope here -- `teaching_session.join.join_session` doesn't emit an event
    (see its own docstring), and "significant events" (base AC1) doesn't
    include joins, so there is no join-derived state to fold. Add a
    `student_joined` event type first if a live roster count is ever needed.
    """

    session_id: str
    current_slide_id: str | None = None
    current_branch_id: str | None = None
    open_interaction_id: str | None = None
    tallies: dict[str, dict[str, int]] = field(default_factory=dict)
    ended: bool = False
    last_sequence: int = 0
    updated_at: datetime | None = None


def initial_read_model(session_id: str) -> SessionReadModel:
    return SessionReadModel(session_id=session_id)


def apply_event(state: SessionReadModel, event: SessionEvent) -> SessionReadModel:
    """Fold one event into the read model. Last-write-wins per field (see module docstring)."""
    next_state = state
    match event.event_type:
        case SessionEventType.SLIDE_CHANGED:
            payload = SlideChangedPayload.model_validate(event.payload)
            next_state = replace(next_state, current_slide_id=payload.slide_id)
        case SessionEventType.BRANCH_SELECTED:
            payload = BranchSelectedPayload.model_validate(event.payload)
            next_state = replace(
                next_state, current_slide_id=payload.slide_id, current_branch_id=payload.branch_id,
            )
        case SessionEventType.INTERACTION_OPENED:
            payload = InteractionOpenedPayload.model_validate(event.payload)
            next_state = replace(next_state, open_interaction_id=payload.interaction_id)
        case SessionEventType.AGGREGATE_UPDATED:
            payload = AggregateUpdatedPayload.model_validate(event.payload)
            tallies = dict(next_state.tallies)
            tallies[payload.interaction_id] = payload.tallies
            next_state = replace(next_state, tallies=tallies)
        case SessionEventType.SESSION_ENDED:
            next_state = replace(next_state, ended=True)
        case SessionEventType.SESSION_STARTED | SessionEventType.ANNOTATION_ADDED:
            pass  # no read-model field derived from these yet -- event is still logged/broadcast
    if event.sequence is not None:
        last_sequence = max(next_state.last_sequence, event.sequence)
        next_state = replace(next_state, last_sequence=last_sequence)
    return replace(next_state, updated_at=event.created_at)
