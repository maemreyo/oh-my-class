from __future__ import annotations

"""Unit-scoped observability helpers — emit events and tags for unit runs."""

from dataclasses import dataclass

from common.contracts.lesson_sequence import LessonSequence


@dataclass
class UnitObservabilityEvent:
    """Structured event emitted at key lifecycle points of a unit plan run.

    Callers are responsible for forwarding the event to Langfuse or the
    teaching-pack event bus — construction is intentionally side-effect free.
    """

    event_name: str
    parent_run_id: str | None
    session_id: str | None
    unit_role: str
    grounding_status: str | None
    confidence: float | None
    fan_out_size: int | None
    session_count_norm: int | None
    tokens_used: int | None
    cost_usd: float | None
    blocked_count: int | None
    edit_count: int | None


def emit_unit_created(
    parent_run_id: str,
    sequence: LessonSequence,
    grounding_status: str,
) -> UnitObservabilityEvent:
    """Build an event representing the initial creation of a unit plan.

    Callers emit the returned object to Langfuse or the event bus separately.
    """
    return UnitObservabilityEvent(
        event_name="unit.created",
        parent_run_id=parent_run_id,
        session_id=None,
        unit_role="parent",
        grounding_status=grounding_status,
        confidence=sequence.confidence,
        fan_out_size=len(sequence.sessions),
        session_count_norm=sequence.total_sessions,
        tokens_used=None,
        cost_usd=None,
        blocked_count=None,
        edit_count=None,
    )


def emit_session_status_changed(
    parent_run_id: str,
    session_id: str,
    status: str,
) -> UnitObservabilityEvent:
    """Build an event for a child session transitioning to a new status.

    Callers emit the returned object to Langfuse or the event bus separately.
    The ``status`` value is not stored on the dataclass; callers should attach
    it to the event payload when forwarding to the bus.
    """
    return UnitObservabilityEvent(
        event_name="unit.session.status_changed",
        parent_run_id=parent_run_id,
        session_id=session_id,
        unit_role="session",
        grounding_status=None,
        confidence=None,
        fan_out_size=None,
        session_count_norm=None,
        tokens_used=None,
        cost_usd=None,
        blocked_count=None,
        edit_count=None,
    )


def emit_unit_completed(
    parent_run_id: str,
    total_sessions: int,
    approved: int,
    failed: int,
    tokens_used: int,
    cost_usd: float,
) -> UnitObservabilityEvent:
    """Build a summary event after all child sessions have finished.

    ``blocked_count`` is derived as ``total_sessions - approved - failed``
    (sessions that were neither approved nor recorded as failed).

    Callers emit the returned object to Langfuse or the event bus separately.
    """
    blocked = max(0, total_sessions - approved - failed)
    return UnitObservabilityEvent(
        event_name="unit.completed",
        parent_run_id=parent_run_id,
        session_id=None,
        unit_role="parent",
        grounding_status=None,
        confidence=None,
        fan_out_size=total_sessions,
        session_count_norm=total_sessions,
        tokens_used=tokens_used,
        cost_usd=cost_usd,
        blocked_count=blocked,
        edit_count=None,
    )


def unit_attribution_tags(
    parent_run_id: str,
    session_id: str | None = None,
    unit_role: str = "parent",
) -> dict[str, str | None]:
    """Return a tags dict for extending ``teaching_pack_thread_config``.

    Used for child cost attribution so that Langfuse and the cost ledger can
    group token spend back to the parent unit run.

    Example::

        config = {
            **teaching_pack_thread_config(run_id),
            "metadata": unit_attribution_tags(parent_run_id, session_id, "session"),
        }
    """
    return {
        "parent_run_id": parent_run_id,
        "session_id": session_id,
        "unit_role": unit_role,
    }
