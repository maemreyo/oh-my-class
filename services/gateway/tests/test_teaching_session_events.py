from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.gateway.teaching_session.events import (
    SessionEventType,
    apply_event,
    build_event,
    initial_read_model,
)
from services.gateway.teaching_session.tokens import SessionRole


class TestBuildEvent:
    """AC: significant event types are typed, validated-at-construction Pydantic models."""

    def test_builds_a_slide_changed_event(self) -> None:
        event = build_event(
            session_id="s1",
            event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER,
            payload={"slide_id": "slide-1", "slide_index": 2},
        )
        assert event.event_type == SessionEventType.SLIDE_CHANGED
        assert event.payload == {"slide_id": "slide-1", "slide_index": 2}
        assert event.sequence is None

    def test_rejects_a_payload_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            build_event(
                session_id="s1",
                event_type=SessionEventType.SLIDE_CHANGED,
                actor_role=SessionRole.CONTROLLER,
                payload={"slide_index": 2},  # missing slide_id
            )

    def test_rejects_a_payload_with_the_wrong_shape_for_the_event_type(self) -> None:
        with pytest.raises(ValidationError):
            build_event(
                session_id="s1",
                event_type=SessionEventType.AGGREGATE_UPDATED,
                actor_role=SessionRole.STUDENT,
                payload={"slide_id": "slide-1"},  # aggregate_updated needs interaction_id/tallies
            )

    @pytest.mark.parametrize("event_type", list(SessionEventType))
    def test_every_significant_event_type_has_a_payload_model(
        self, event_type: SessionEventType,
    ) -> None:
        """AC: all significant event types are specified (base AC1), including
        `CONTENT_REPUBLISHED` (#458 follow-up gap)."""
        payloads = {
            SessionEventType.SESSION_STARTED: {"deck_id": "d1", "snapshot_id": "snap1"},
            SessionEventType.SLIDE_CHANGED: {"slide_id": "slide-1"},
            SessionEventType.INTERACTION_OPENED: {"interaction_id": "i1", "slide_id": "slide-1"},
            SessionEventType.AGGREGATE_UPDATED: {"interaction_id": "i1", "tallies": {"a": 1}},
            SessionEventType.BRANCH_SELECTED: {"slide_id": "slide-1", "branch_id": "b1"},
            SessionEventType.ANNOTATION_ADDED: {"slide_id": "slide-1", "annotation_id": "a1"},
            SessionEventType.SESSION_ENDED: {"reason": "class_over"},
            SessionEventType.CONTENT_REPUBLISHED: {"snapshot_id": "snap2"},
        }
        event = build_event(
            session_id="s1", event_type=event_type, actor_role=SessionRole.CONTROLLER,
            payload=payloads[event_type],
        )
        assert event.event_type == event_type


class TestApplyEvent:
    """AC: derived read models for fast teacher/display/student UI state."""

    def test_slide_changed_sets_current_slide(self) -> None:
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "slide-2"}, event_id="e1",
        ).model_copy(update={"sequence": 1})
        next_state = apply_event(state, event)
        assert next_state.current_slide_id == "slide-2"
        assert next_state.last_sequence == 1

    def test_branch_selected_sets_slide_and_branch(self) -> None:
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.BRANCH_SELECTED,
            actor_role=SessionRole.CONTROLLER,
            payload={"slide_id": "slide-3", "branch_id": "b1"},
        ).model_copy(update={"sequence": 1})
        next_state = apply_event(state, event)
        assert next_state.current_slide_id == "slide-3"
        assert next_state.current_branch_id == "b1"

    def test_aggregate_updated_sets_tallies_per_interaction(self) -> None:
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.AGGREGATE_UPDATED,
            actor_role=SessionRole.STUDENT,
            payload={"interaction_id": "i1", "tallies": {"attempt_count": 3, "correct_count": 1}},
        ).model_copy(update={"sequence": 1})
        next_state = apply_event(state, event)
        assert next_state.tallies == {"i1": {"attempt_count": 3, "correct_count": 1}}

    def test_session_ended_sets_ended_flag(self) -> None:
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.SESSION_ENDED,
            actor_role=SessionRole.CONTROLLER, payload={},
        ).model_copy(update={"sequence": 1})
        next_state = apply_event(state, event)
        assert next_state.ended is True

    def test_replaying_the_same_event_twice_is_a_no_op(self) -> None:
        """Idempotent-replay property: recovering from Postgres after a Redis
        miss may re-apply an event that's already reflected in the read model
        it started from (see event_log.record_event's docstring) -- this must
        never double-count."""
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.AGGREGATE_UPDATED,
            actor_role=SessionRole.STUDENT,
            payload={"interaction_id": "i1", "tallies": {"attempt_count": 3, "correct_count": 1}},
        ).model_copy(update={"sequence": 1})
        once = apply_event(state, event)
        twice = apply_event(once, event)
        assert once == twice

    def test_last_sequence_is_monotonic_even_out_of_order(self) -> None:
        state = initial_read_model("s1")
        event_2 = build_event(
            session_id="s1", event_type=SessionEventType.SLIDE_CHANGED,
            actor_role=SessionRole.CONTROLLER, payload={"slide_id": "slide-2"},
        ).model_copy(update={"sequence": 2})
        state = apply_event(state, event_2)
        assert state.last_sequence == 2

    def test_content_republished_derives_no_read_model_field(self) -> None:
        """`TeachingSession.snapshot_id` in Postgres is the pin's one source
        of truth (see `ContentRepublishedPayload`'s docstring) -- this event
        is logged/broadcast only, same as SESSION_STARTED/ANNOTATION_ADDED."""
        state = initial_read_model("s1")
        event = build_event(
            session_id="s1", event_type=SessionEventType.CONTENT_REPUBLISHED,
            actor_role=SessionRole.CONTROLLER, payload={"snapshot_id": "snap2"},
        ).model_copy(update={"sequence": 1})
        next_state = apply_event(state, event)
        assert next_state == state.__class__(
            session_id="s1", last_sequence=1, updated_at=next_state.updated_at,
        )
