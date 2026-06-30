"""Tests for unit-scoped observability helpers (td-018)."""
from __future__ import annotations

from common.contracts.lesson_sequence import LessonSequence, SessionPlan, KnowledgeComponent
from packages.agents.sub_agents.unit_planner.observability import (
    UnitObservabilityEvent,
    emit_unit_created,
    emit_session_status_changed,
    emit_unit_completed,
    unit_attribution_tags,
)


# ---------------------------------------------------------------------------
# Minimal LessonSequence factory
# ---------------------------------------------------------------------------

def _make_sequence(total_sessions: int = 3) -> LessonSequence:
    sessions = [
        SessionPlan(
            session_id=f"S{i:02d}",
            order_index=i,
            title=f"Session {i}: Test Topic",
            sub_topic=f"Test Topic part {i}",
            duration_minutes=45,
            learning_objectives=[f"Students can understand Test Topic part {i}"],
            bloom_level_primary="understand",
            knowledge_components=[
                KnowledgeComponent(
                    kc_id=f"KC-S{i:02d}-1",
                    title=f"KC {i}",
                    description=f"Core component for session {i}",
                )
            ],
            prerequisite_sessions=[f"S{i - 1:02d}"] if i > 1 else [],
            methodology_primary="concept_map",
        )
        for i in range(1, total_sessions + 1)
    ]
    return LessonSequence(
        topic="Test Topic",
        grade_level="Grade 5",
        subject="Math",
        locale="en",
        total_sessions=total_sessions,
        total_duration_minutes=45 * total_sessions,
        sessions=sessions,
        grounding_status="grounded",
        confidence=0.86,
        rationale="test sequence for observability unit tests",
    )


# ---------------------------------------------------------------------------
# test_emit_unit_created_structure
# ---------------------------------------------------------------------------

def test_emit_unit_created_structure() -> None:
    """emit_unit_created populates all required fields from the LessonSequence."""
    sequence = _make_sequence(total_sessions=3)
    event = emit_unit_created(
        parent_run_id="run-test-001",
        sequence=sequence,
        grounding_status="grounded",
    )

    assert isinstance(event, UnitObservabilityEvent)
    assert event.event_name == "unit.created"
    assert event.parent_run_id == "run-test-001"
    assert event.session_id is None
    assert event.unit_role == "parent"
    assert event.grounding_status == "grounded"
    assert event.confidence == 0.86
    assert event.fan_out_size == 3
    assert event.session_count_norm == 3
    assert event.tokens_used is None
    assert event.cost_usd is None
    assert event.blocked_count is None
    assert event.edit_count is None


# ---------------------------------------------------------------------------
# test_unit_attribution_tags
# ---------------------------------------------------------------------------

def test_unit_attribution_tags() -> None:
    """unit_attribution_tags returns a dict with all required attribution keys."""
    tags = unit_attribution_tags(
        parent_run_id="run-parent-42",
        session_id="S02",
        unit_role="session",
    )

    assert isinstance(tags, dict)
    assert "parent_run_id" in tags, "missing key: parent_run_id"
    assert "session_id" in tags, "missing key: session_id"
    assert "unit_role" in tags, "missing key: unit_role"

    assert tags["parent_run_id"] == "run-parent-42"
    assert tags["session_id"] == "S02"
    assert tags["unit_role"] == "session"


def test_unit_attribution_tags_defaults() -> None:
    """unit_attribution_tags uses 'parent' as default unit_role and None for session_id."""
    tags = unit_attribution_tags(parent_run_id="run-parent-99")

    assert tags["parent_run_id"] == "run-parent-99"
    assert tags["session_id"] is None
    assert tags["unit_role"] == "parent"


# ---------------------------------------------------------------------------
# test_emit_session_status_changed
# ---------------------------------------------------------------------------

def test_emit_session_status_changed() -> None:
    """emit_session_status_changed sets the correct event_name and ids."""
    event = emit_session_status_changed(
        parent_run_id="run-parent-77",
        session_id="S03",
        status="completed",
    )

    assert isinstance(event, UnitObservabilityEvent)
    assert event.event_name == "unit.session.status_changed"
    assert event.parent_run_id == "run-parent-77"
    assert event.session_id == "S03"
    assert event.unit_role == "session"
    # Fields that don't apply to a session-level status event should be None
    assert event.grounding_status is None
    assert event.confidence is None
    assert event.fan_out_size is None
    assert event.tokens_used is None
    assert event.cost_usd is None


# ---------------------------------------------------------------------------
# Additional: emit_unit_completed
# ---------------------------------------------------------------------------

def test_emit_unit_completed_structure() -> None:
    """emit_unit_completed populates token/cost fields and derives blocked_count."""
    event = emit_unit_completed(
        parent_run_id="run-parent-55",
        total_sessions=5,
        approved=3,
        failed=1,
        tokens_used=12000,
        cost_usd=0.048,
    )

    assert isinstance(event, UnitObservabilityEvent)
    assert event.event_name == "unit.completed"
    assert event.parent_run_id == "run-parent-55"
    assert event.session_id is None
    assert event.unit_role == "parent"
    assert event.fan_out_size == 5
    assert event.session_count_norm == 5
    assert event.tokens_used == 12000
    assert event.cost_usd == 0.048
    # 5 total - 3 approved - 1 failed = 1 blocked
    assert event.blocked_count == 1
    assert event.edit_count is None
