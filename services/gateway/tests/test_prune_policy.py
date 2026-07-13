"""Exhaustive, DB-free tests for the OPS-07 prune-eligibility predicate.

This is the safety core of OPS-07 (ADR-034 §5 / ADR-026): every protected
state must return "keep" (not prunable), and only a genuinely clean run may
return "prunable". No mocks/DB needed -- `is_prunable` is pure.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.gateway.models import RunStatus
from services.gateway.prune_policy import (
    FAST_LANE_REVERT_WINDOW_SECONDS,
    RunPruneContext,
    is_prunable,
)

NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=UTC)
RETENTION_DAYS = 30
LONG_AGO = NOW - timedelta(days=RETENTION_DAYS + 1)
JUST_INSIDE = NOW - timedelta(days=RETENTION_DAYS - 1)


def _ctx(**overrides: object) -> RunPruneContext:
    base: dict[str, object] = {
        "run_id": "run-1",
        "status": RunStatus.COMPLETED,
        "deleted_at": LONG_AGO,
        "has_open_gate": False,
        "fast_lane_approved_at": None,
        "export_finalized": False,
    }
    base.update(overrides)
    return RunPruneContext(**base)  # type: ignore[arg-type]


class TestPendingRunsAreNeverPruned:
    def test_pending_status_kept(self) -> None:
        assert is_prunable(_ctx(status=RunStatus.PENDING), RETENTION_DAYS, now=NOW) is False

    def test_awaiting_approval_kept(self) -> None:
        ctx = _ctx(status=RunStatus.AWAITING_APPROVAL)
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is False

    def test_every_non_terminal_status_kept(self) -> None:
        non_terminal = set(RunStatus) - {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
        assert non_terminal, "sanity: there should be non-terminal statuses"
        for status in non_terminal:
            assert is_prunable(_ctx(status=status), RETENTION_DAYS, now=NOW) is False


class TestEscalatedOrOpenGatesAreNeverPruned:
    def test_open_gate_on_terminal_run_kept(self) -> None:
        # Terminal status can still coexist with a leftover open/escalated
        # gate row (e.g. run cancelled while a gate was mid-flight) -- must
        # still be kept.
        assert is_prunable(_ctx(has_open_gate=True), RETENTION_DAYS, now=NOW) is False


class TestRetentionNotYetElapsedIsKept:
    def test_not_soft_deleted_kept(self) -> None:
        assert is_prunable(_ctx(deleted_at=None), RETENTION_DAYS, now=NOW) is False

    def test_soft_deleted_but_inside_window_kept(self) -> None:
        assert is_prunable(_ctx(deleted_at=JUST_INSIDE), RETENTION_DAYS, now=NOW) is False


class TestAdr026RevisionWindow:
    """The safety property the issue calls out by name: a run inside its
    ADR-026 revert window is never pruned, even if it's otherwise past
    retention and terminal."""

    def test_fast_laned_but_export_not_finalized_kept_even_past_retention(self) -> None:
        ctx = _ctx(
            fast_lane_approved_at=LONG_AGO,
            export_finalized=False,
        )
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is False

    def test_fast_laned_and_finalized_but_inside_revert_window_kept(self) -> None:
        approved_at = NOW - timedelta(seconds=FAST_LANE_REVERT_WINDOW_SECONDS - 1)
        ctx = _ctx(
            deleted_at=LONG_AGO,
            fast_lane_approved_at=approved_at,
            export_finalized=True,
        )
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is False

    def test_fast_laned_exactly_at_window_boundary_kept(self) -> None:
        # now == window_closes_at is still inside (strict `now <` deny check
        # means the boundary instant itself is protected) -- fail-closed on
        # the edge rather than off-by-one into deleting on the exact second.
        approved_at = NOW - timedelta(seconds=FAST_LANE_REVERT_WINDOW_SECONDS)
        ctx = _ctx(deleted_at=LONG_AGO, fast_lane_approved_at=approved_at, export_finalized=True)
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is True

    def test_fast_laned_and_finalized_and_window_elapsed_prunable(self) -> None:
        approved_at = NOW - timedelta(seconds=FAST_LANE_REVERT_WINDOW_SECONDS + 1)
        ctx = _ctx(
            deleted_at=LONG_AGO,
            fast_lane_approved_at=approved_at,
            export_finalized=True,
        )
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is True

    def test_never_fast_laned_ignores_window_entirely(self) -> None:
        # Manual approval (no fast lane) has no revert window to wait out.
        ctx = _ctx(fast_lane_approved_at=None, export_finalized=False)
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is True


class TestGenuinelyEligibleRunIsPruned:
    def test_clean_terminal_run_past_retention_is_prunable(self) -> None:
        assert is_prunable(_ctx(), RETENTION_DAYS, now=NOW) is True

    def test_failed_run_past_retention_is_prunable(self) -> None:
        assert is_prunable(_ctx(status=RunStatus.FAILED), RETENTION_DAYS, now=NOW) is True

    def test_cancelled_run_past_retention_is_prunable(self) -> None:
        assert is_prunable(_ctx(status=RunStatus.CANCELLED), RETENTION_DAYS, now=NOW) is True


class TestAmbiguousCasesDefaultToNoPrune:
    def test_open_gate_and_past_retention_and_terminal_still_kept(self) -> None:
        # Multiple independent protective conditions compound to "keep" --
        # the predicate never lets a second bad signal cancel out a good one.
        ctx = _ctx(has_open_gate=True, fast_lane_approved_at=LONG_AGO, export_finalized=False)
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is False

    def test_fast_lane_timestamp_present_without_finalize_flag_never_races_to_true(self) -> None:
        # Even if a caller forgets to populate export_finalized correctly
        # (defaults to False), the predicate still refuses rather than
        # assuming finalized.
        ctx = _ctx(fast_lane_approved_at=NOW, export_finalized=False)
        assert is_prunable(ctx, RETENTION_DAYS, now=NOW) is False


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
