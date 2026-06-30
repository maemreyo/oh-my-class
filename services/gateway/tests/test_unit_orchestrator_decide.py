"""Tests for the pure decide() function in unit_orchestrator.py (td-010).

All tests are pure — no DB, no I/O.  They build minimal ``LessonSequence``
objects using the real Pydantic models and verify the action list returned by
``decide()``.
"""

from __future__ import annotations

import pytest

from common.contracts.lesson_sequence import LessonSequence, SessionPlan
from services.gateway.models import RunStatus
from services.gateway.unit_orchestrator import OrchestratorAction, SessionAction, decide

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_METHODOLOGY: str = "concept_map"


def _make_session(
    session_id: str,
    order_index: int,
    *,
    prerequisite_sessions: list[str] | None = None,
) -> SessionPlan:
    return SessionPlan(
        session_id=session_id,
        order_index=order_index,
        title=f"Session {session_id}",
        sub_topic=f"Sub-topic {session_id}",
        duration_minutes=30,
        learning_objectives=["Objective one"],
        bloom_level_primary="understand",
        methodology_primary=_METHODOLOGY,
        prerequisite_sessions=prerequisite_sessions or [],
    )


def _seq(*session_specs: tuple[str, list[str]]) -> LessonSequence:
    """Build a minimal ``LessonSequence`` from (session_id, prereqs) tuples."""
    sessions = [
        _make_session(sid, idx + 1, prerequisite_sessions=prereqs)
        for idx, (sid, prereqs) in enumerate(session_specs)
    ]
    return LessonSequence(
        topic="Test Unit",
        grade_level="Grade 5",
        subject="Math",
        locale="en",
        total_sessions=len(sessions),
        total_duration_minutes=len(sessions) * 30,
        sessions=sessions,
        grounding_status="grounded",
        confidence=0.9,
        rationale="Test fixture",
    )


def _actions_for(actions: list[SessionAction], kind: OrchestratorAction) -> list[SessionAction]:
    return [a for a in actions if a.action is kind]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDecideDiamondDag:
    def test_only_root_spawned_when_all_unspawned(self) -> None:
        """Diamond DAG: A→B, A→C, B+C→D.  All unspawned, concurrency=4.

        Only A has no prerequisites so only A should be spawned.
        """
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
            ("C", ["A"]),
            ("D", ["B", "C"]),
        )
        actions = decide(sequence, children_states={}, unit_fanout_concurrency=4)

        spawns = _actions_for(actions, OrchestratorAction.SPAWN)
        assert len(spawns) == 1
        assert spawns[0].session_id == "A"

        # B, C, D should not appear (not BLOCK either — they're just not ready).
        non_spawn_session_ids = {a.session_id for a in actions if a.action is not OrchestratorAction.SPAWN}
        assert "B" not in non_spawn_session_ids
        assert "C" not in non_spawn_session_ids
        assert "D" not in non_spawn_session_ids


class TestDecideSpawnsDependents:
    def test_spawns_b_and_c_after_a_completes(self) -> None:
        """A completed, B and C unspawned and both depend only on A.

        With concurrency=2 both B and C should be spawned.
        """
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
            ("C", ["A"]),
        )
        children_states: dict[str, RunStatus] = {"A": RunStatus.COMPLETED}
        actions = decide(sequence, children_states, unit_fanout_concurrency=2)

        spawns = _actions_for(actions, OrchestratorAction.SPAWN)
        spawned_ids = {a.session_id for a in spawns}
        assert spawned_ids == {"B", "C"}


class TestDecideBlocksDependentsOfFailedNode:
    def test_b_blocked_when_a_failed(self) -> None:
        """A failed → B (which depends on A) should be BLOCKED."""
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
        )
        children_states: dict[str, RunStatus] = {"A": RunStatus.FAILED}
        actions = decide(sequence, children_states, unit_fanout_concurrency=4)

        blocks = _actions_for(actions, OrchestratorAction.BLOCK)
        assert len(blocks) == 1
        assert blocks[0].session_id == "B"
        assert "A" in blocks[0].reason

    def test_cancelled_prereq_also_blocks(self) -> None:
        """CANCELLED counts as failed for the purposes of blocking dependents."""
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
        )
        children_states: dict[str, RunStatus] = {"A": RunStatus.CANCELLED}
        actions = decide(sequence, children_states, unit_fanout_concurrency=4)

        blocks = _actions_for(actions, OrchestratorAction.BLOCK)
        assert any(a.session_id == "B" for a in blocks)


class TestDecideMarkComplete:
    def test_marks_complete_when_all_sessions_completed(self) -> None:
        """All sessions COMPLETED → MARK_COMPLETE action is appended."""
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
        )
        children_states: dict[str, RunStatus] = {
            "A": RunStatus.COMPLETED,
            "B": RunStatus.COMPLETED,
        }
        actions = decide(sequence, children_states, unit_fanout_concurrency=1)

        complete_actions = _actions_for(actions, OrchestratorAction.MARK_COMPLETE)
        assert len(complete_actions) == 1

    def test_no_mark_complete_when_only_some_done(self) -> None:
        """Partial completion must not produce MARK_COMPLETE."""
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
        )
        children_states: dict[str, RunStatus] = {"A": RunStatus.COMPLETED}
        actions = decide(sequence, children_states, unit_fanout_concurrency=1)

        assert not _actions_for(actions, OrchestratorAction.MARK_COMPLETE)


class TestDecideMarkPartiallyComplete:
    def test_marks_partially_complete_when_some_failed_and_rest_done(self) -> None:
        """A: completed, B: failed, C (no prereqs): completed, D depends B: blocked.

        Expected: BLOCK D, MARK_PARTIALLY_COMPLETE (no active/spawnable sessions).
        """
        sequence = _seq(
            ("A", []),
            ("B", []),
            ("C", []),
            ("D", ["B"]),
        )
        children_states: dict[str, RunStatus] = {
            "A": RunStatus.COMPLETED,
            "B": RunStatus.FAILED,
            "C": RunStatus.COMPLETED,
        }
        actions = decide(sequence, children_states, unit_fanout_concurrency=1)

        block_actions = _actions_for(actions, OrchestratorAction.BLOCK)
        assert any(a.session_id == "D" for a in block_actions)

        partial_actions = _actions_for(actions, OrchestratorAction.MARK_PARTIALLY_COMPLETE)
        assert len(partial_actions) == 1

    def test_no_partial_when_active_sessions_remain(self) -> None:
        """If some sessions are still active, do not emit MARK_PARTIALLY_COMPLETE."""
        sequence = _seq(
            ("A", []),
            ("B", []),
        )
        children_states: dict[str, RunStatus] = {
            "A": RunStatus.FAILED,
            "B": RunStatus.GENERATING,
        }
        actions = decide(sequence, children_states, unit_fanout_concurrency=1)
        assert not _actions_for(actions, OrchestratorAction.MARK_PARTIALLY_COMPLETE)


class TestDecideConcurrencyCap:
    def test_caps_spawns_at_concurrency_limit(self) -> None:
        """5 unspawned sessions all with no prerequisites, cap=2 → only 2 SPAWNs."""
        sequence = _seq(
            ("A", []),
            ("B", []),
            ("C", []),
            ("D", []),
            ("E", []),
        )
        actions = decide(sequence, children_states={}, unit_fanout_concurrency=2)

        spawns = _actions_for(actions, OrchestratorAction.SPAWN)
        assert len(spawns) == 2

    def test_concurrency_one_spawns_exactly_one(self) -> None:
        """Default concurrency of 1 spawns at most one session per call."""
        sequence = _seq(
            ("A", []),
            ("B", []),
            ("C", []),
        )
        actions = decide(sequence, children_states={}, unit_fanout_concurrency=1)

        spawns = _actions_for(actions, OrchestratorAction.SPAWN)
        assert len(spawns) == 1

    def test_concurrency_zero_spawns_nothing(self) -> None:
        """concurrency=0 means no spawns are allowed this tick."""
        sequence = _seq(
            ("A", []),
        )
        actions = decide(sequence, children_states={}, unit_fanout_concurrency=0)

        assert not _actions_for(actions, OrchestratorAction.SPAWN)


class TestDecideIdempotency:
    def test_already_spawned_sessions_not_re_spawned(self) -> None:
        """Sessions already present in children_states are not spawned again."""
        sequence = _seq(
            ("A", []),
            ("B", ["A"]),
        )
        children_states: dict[str, RunStatus] = {"A": RunStatus.PENDING}
        actions = decide(sequence, children_states, unit_fanout_concurrency=4)

        spawns = _actions_for(actions, OrchestratorAction.SPAWN)
        assert not any(a.session_id == "A" for a in spawns)

    def test_active_session_not_blocked_or_spawned(self) -> None:
        """A session that is GENERATING should not appear in any action."""
        sequence = _seq(("A", []))
        children_states: dict[str, RunStatus] = {"A": RunStatus.GENERATING}
        actions = decide(sequence, children_states, unit_fanout_concurrency=4)

        session_ids_in_actions = {a.session_id for a in actions if a.session_id}
        assert "A" not in session_ids_in_actions
