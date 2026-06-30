"""Tests for UnitOrchestrator concurrency cap.

Verifies that unit_fanout_concurrency correctly limits how many sessions
are spawned in a single decide() call.
"""
from __future__ import annotations

import pytest

from common.contracts.lesson_sequence import LessonSequence, SessionPlan
from services.gateway.models import RunStatus
from services.gateway.unit_orchestrator import OrchestratorAction, decide


_METHODOLOGY = "concept_map"


def _make_session(session_id: str, order_index: int, *, prereqs: list[str] | None = None) -> SessionPlan:
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=f"Session {session_id}",
        sub_topic=f"Sub-topic {session_id}",
        duration_minutes=30,
        learning_objectives=["Objective"],
        bloom_level_primary="understand",
        methodology_primary=_METHODOLOGY,
        prerequisite_sessions=prereqs or [],
    )


def _flat_seq(n: int) -> LessonSequence:
    """n independent sessions (no prerequisites)."""
    sessions = [_make_session(str(i), i) for i in range(1, n + 1)]
    return LessonSequence(
        topic="Unit",
        grade_level="Grade 5",
        subject="Math",
        locale="en",
        total_sessions=n,
        total_duration_minutes=n * 30,
        sessions=sessions,
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test",
    )


def test_cap_1_spawns_one_at_a_time() -> None:
    """With cap=1 and 5 ready sessions, only 1 SPAWN action is emitted."""
    seq = _flat_seq(5)
    actions = decide(seq, {}, unit_fanout_concurrency=1)
    spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
    assert len(spawns) == 1


def test_cap_n_spawns_full_ready_layer() -> None:
    """With cap=5, all 5 unspawned independent sessions are spawned at once."""
    seq = _flat_seq(5)
    actions = decide(seq, {}, unit_fanout_concurrency=5)
    spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
    assert len(spawns) == 5


def test_cap_larger_than_ready_set() -> None:
    """Cap larger than the ready set — spawns only the actual ready sessions."""
    seq = _flat_seq(3)
    actions = decide(seq, {}, unit_fanout_concurrency=10)
    spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
    assert len(spawns) == 3


def test_cap_respected_when_some_already_running() -> None:
    """With cap=2 and 1 already active (pending), only 2 new sessions can be spawned."""
    seq = _flat_seq(5)
    # session "1" is already active (does not appear as unspawned)
    children_states = {"1": RunStatus.PENDING}
    actions = decide(seq, children_states, unit_fanout_concurrency=2)
    spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
    # 4 sessions remaining, cap=2 → only 2 spawned
    assert len(spawns) == 2


def test_sequential_topological_order_with_cap_1() -> None:
    """Cap=1 with a chain A→B→C: only A is spawned (B+C not ready)."""
    sessions = [
        _make_session("A", 1, prereqs=[]),
        _make_session("B", 2, prereqs=["A"]),
        _make_session("C", 3, prereqs=["B"]),
    ]
    seq = LessonSequence(
        topic="Chain",
        grade_level="Grade 5",
        subject="Math",
        locale="en",
        total_sessions=3,
        total_duration_minutes=90,
        sessions=sessions,
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test",
    )
    actions = decide(seq, {}, unit_fanout_concurrency=1)
    spawns = [a for a in actions if a.action is OrchestratorAction.SPAWN]
    assert len(spawns) == 1
    assert spawns[0].session_id == "A"
