from __future__ import annotations

from packages.agents.events import ObservabilityEvent
from services.gateway.observability_events import (
    observability_event_payload,
    observability_event_row,
)
from services.gateway.teaching_pack_models import TeachingPackEventVisibility


def test_observability_event_payload_preserves_typed_fields() -> None:
    event = ObservabilityEvent(
        run_id="run-1",
        event_type="healing_decision",
        payload={"healing_strategy": "retry"},
        teacher_id="teacher-1",
        stage="render_quality",
    )

    payload = observability_event_payload(event)

    assert payload["event_id"] == event.event_id
    assert payload["observability_event_type"] == "healing_decision"
    assert payload["payload"] == {"healing_strategy": "retry"}
    assert payload["teacher_id"] == "teacher-1"
    assert isinstance(payload["timestamp"], str)


def test_observability_event_row_targets_run_events_shape() -> None:
    event = ObservabilityEvent(
        run_id="run-1",
        event_type="stage_transition",
        payload={"stage": "setup_contract"},
        stage="setup_contract",
    )

    row = observability_event_row(event, sequence=3, visibility=TeachingPackEventVisibility.TEACHER)

    assert row.run_id == "run-1"
    assert row.sequence == 3
    assert row.event_name == "stage_transition"
    assert row.stage == "setup_contract"
    assert row.visibility is TeachingPackEventVisibility.TEACHER
    assert row.payload is not None
    assert row.payload["observability_event_type"] == "stage_transition"
    assert row.payload["payload"] == {"stage": "setup_contract"}
