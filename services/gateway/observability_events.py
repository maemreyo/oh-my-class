from __future__ import annotations

from packages.agents.events import ObservabilityEvent
from services.gateway.teaching_pack_models import RunEvent, TeachingPackEventVisibility
from services.gateway.teaching_pack_types import JsonObject


def observability_event_payload(event: ObservabilityEvent) -> JsonObject:
    payload: JsonObject = {
        "event_id": event.event_id,
        "observability_event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "payload": event.payload,
    }
    if event.teacher_id is not None:
        payload["teacher_id"] = event.teacher_id
    return payload


def observability_event_row(
    event: ObservabilityEvent,
    sequence: int,
    visibility: TeachingPackEventVisibility,
) -> RunEvent:
    return RunEvent(
        run_id=event.run_id,
        sequence=sequence,
        event_name=event.event_type,
        stage=event.stage,
        visibility=visibility,
        payload=observability_event_payload(event),
    )
