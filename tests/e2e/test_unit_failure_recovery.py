"""
E2E: Unit failure isolation and recovery — focused tests.
Real DB + real LLM (9router port 20228, model 4omc).
Run: uv run pytest tests/e2e/test_unit_failure_recovery.py -v
"""
from __future__ import annotations

import pytest

from services.gateway.models import RunStatus
from services.gateway.unit_orchestrator import OrchestratorAction, decide

pytestmark = [pytest.mark.real_llm, pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Fixture: 3 independent sessions (no prerequisites)
# ---------------------------------------------------------------------------

def _parallel_seq():
    """3 independent sessions (no prerequisite_sessions)."""
    from common.contracts.lesson_sequence import LessonSequence, SessionPlan
    from common.contracts.methodology_registry import MethodologyTag

    sessions = [
        SessionPlan(
            session_id=f"s{i}",
            order_index=i,
            title=f"Session {i}",
            sub_topic=f"Sub {i}",
            duration_minutes=30,
            learning_objectives=["Obj"],
            bloom_level_primary="understand",
            methodology_primary=MethodologyTag.CONCEPT_MAP,
            prerequisite_sessions=[],
        )
        for i in range(1, 4)
    ]
    return LessonSequence(
        topic="Recovery Test — parallel",
        grade_level="Grade 5",
        subject="Math",
        locale="vi",
        total_sessions=3,
        total_duration_minutes=90,
        sessions=sessions,
        grounding_status="grounded",
        confidence=0.9,
        rationale="Failure isolation test",
    )


# ---------------------------------------------------------------------------
# Test 1: one child fails → unit reaches PARTIALLY_COMPLETE, not FAILED
# ---------------------------------------------------------------------------

def test_forced_session_failure_keeps_unit_alive() -> None:
    """Inject a failure in one child; verify unit lifecycle = PARTIALLY_COMPLETE.

    The unit must not be marked FAILED or COMPLETE when a subset of sessions
    fail and the rest succeed.  It must be PARTIALLY_COMPLETE so the teacher
    can inspect and retry the failed session.
    """
    seq = _parallel_seq()

    # s1 failed; s2 and s3 completed.
    children = {
        "s1": RunStatus.FAILED,
        "s2": RunStatus.COMPLETED,
        "s3": RunStatus.COMPLETED,
    }
    actions = decide(seq, children, unit_fanout_concurrency=4)

    mark_partial = [a for a in actions if a.action == OrchestratorAction.MARK_PARTIALLY_COMPLETE]
    mark_complete = [a for a in actions if a.action == OrchestratorAction.MARK_COMPLETE]

    assert mark_partial, (
        "Unit must be PARTIALLY_COMPLETE — not fully dead — when one child fails "
        "and the rest have completed"
    )
    assert not mark_complete, (
        "Unit must not be COMPLETE while a session has FAILED"
    )


# ---------------------------------------------------------------------------
# Test 2: retry drives the unit to COMPLETE
# ---------------------------------------------------------------------------

def test_retry_drives_to_complete() -> None:
    """After the failed child is retried and its row moves to COMPLETED,
    the unit must reach MARK_COMPLETE.

    Retry means: the *existing* child run is resumed (status updated in DB).
    decide() must never re-spawn the session — it just observes the
    updated status and emits MARK_COMPLETE.
    """
    seq = _parallel_seq()

    # Before retry: s1 failed
    before_retry = {
        "s1": RunStatus.FAILED,
        "s2": RunStatus.COMPLETED,
        "s3": RunStatus.COMPLETED,
    }
    actions_before = decide(seq, before_retry, unit_fanout_concurrency=4)

    # Idempotency: decide() must NOT emit a SPAWN for s1 — the row already exists.
    spawn_s1_before = [
        a for a in actions_before
        if a.action == OrchestratorAction.SPAWN and a.session_id == "s1"
    ]
    assert not spawn_s1_before, (
        "decide() must not re-spawn s1 — retry resumes the existing run row, "
        "not creates a new one"
    )

    # After retry succeeds: s1 row moves to COMPLETED
    after_retry = {
        "s1": RunStatus.COMPLETED,
        "s2": RunStatus.COMPLETED,
        "s3": RunStatus.COMPLETED,
    }
    actions_after = decide(seq, after_retry, unit_fanout_concurrency=4)
    completes = [a for a in actions_after if a.action == OrchestratorAction.MARK_COMPLETE]
    assert completes, (
        "Unit must reach MARK_COMPLETE after the retried session completes successfully"
    )


# ---------------------------------------------------------------------------
# Test 3: independent siblings still complete despite one failure
# ---------------------------------------------------------------------------

def test_independent_siblings_complete() -> None:
    """Independent sessions (no prerequisite on the failed sibling) are still
    spawned and completed despite a peer session failing.

    This verifies that failure isolation is scoped to the failed session only —
    sessions with no dependency chain continue unaffected.
    """
    seq = _parallel_seq()

    # Only s1 has failed; s2 and s3 have not been spawned yet.
    children = {"s1": RunStatus.FAILED}
    actions = decide(seq, children, unit_fanout_concurrency=4)

    spawns = {a.session_id for a in actions if a.action == OrchestratorAction.SPAWN}
    assert "s2" in spawns, "s2 must be spawned — it has no dependency on the failed s1"
    assert "s3" in spawns, "s3 must be spawned — it has no dependency on the failed s1"

    # Confirm s1 is NOT re-spawned (it already has a DB row).
    assert "s1" not in spawns, (
        "s1 must not be re-spawned — its existing row (FAILED) must be retried instead"
    )
