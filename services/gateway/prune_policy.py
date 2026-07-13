"""Revision-window-aware prune-eligibility policy (OPS-07, ADR-034 §5, ADR-026).

``is_prunable`` is the safety core of OPS-07: a pure, default-deny function
with no I/O, so every protected state described in ADR-026 can be exhaustively
unit-tested without a database. Callers gather a ``RunPruneContext`` once per
run (see ``build_run_prune_context``) and re-check it against each data
class's retention window via ``is_prunable``.

ADR-026 boundary this module encodes (see
``docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`` §4): a fast-lane
auto-approval is *revertible* -- the teacher can undo it -- until the
downstream ``export_finalize`` stage materializes. In this codebase that
revert window is concretely ``revert_window_seconds = 900`` on the gate
payload (`packages/agents/teaching_pack/nodes.py:668`), and export_finalize
materializing is recorded as a ``stage="export_finalize"`` row in
``run_status_history`` (`services/gateway/teaching_pack_completion.py:91-94`).
A run is protected until *both* export_finalize has happened *and* the revert
window has elapsed -- if we can't prove either, we fail closed and refuse to
prune.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from services.gateway.models import Run, RunStatus
from services.gateway.retention import is_expired
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    RunEvent,
    RunStatusHistory,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Only these run states are even *candidates* for pruning -- everything else
# is "pending" in ADR-034 §5's sense (still mid-flight).
TERMINAL_RUN_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})

# Gate states that mean "still open or unresolved" -- ACTIVE is awaiting a
# teacher response; EXPIRED is the recovery sweeper's escalation outcome
# (`services/gateway/recovery_sweeper.py::sweep_escalated_gates`) for a gate
# nobody answered in time. Neither is safe to prune underneath.
_OPEN_GATE_STATUSES = frozenset({GateInterruptStatus.ACTIVE, GateInterruptStatus.EXPIRED})

_AUTO_APPROVED_EVENT_NAME = "teaching_pack.content_approval.auto_approved"
_EXPORT_FINALIZE_STAGE = "export_finalize"

# ADR-026 §4's revert window, single-sourced from
# `packages/agents/teaching_pack/nodes.py:668`
# (``gate_payload["revert_window_seconds"] = 900``). Kept here as the prune
# policy's copy of the same constant so this module doesn't silently drift
# from the gate code; if that literal ever becomes a tunable, update both.
FAST_LANE_REVERT_WINDOW_SECONDS: int = 900


@dataclass(frozen=True, slots=True)
class RunPruneContext:
    """Everything ``is_prunable`` needs for one run -- deliberately DB-free."""

    run_id: str
    status: RunStatus
    deleted_at: datetime | None
    has_open_gate: bool
    fast_lane_approved_at: datetime | None
    export_finalized: bool


def is_prunable(
    ctx: RunPruneContext,
    retention_days: int,
    *,
    now: datetime | None = None,
) -> bool:
    """Return True only if *ctx* is provably safe to hard-delete.

    Every clause is a deny check: the function returns ``False`` the moment
    any protective condition can't be ruled out, and only reaches ``True`` at
    the end once nothing objected (default-deny).
    """
    now = now or datetime.now(UTC)

    # 1. Must be terminal. A pending/in-flight run is never prunable.
    if ctx.status not in TERMINAL_RUN_STATUSES:
        return False

    # 2. Must not have a gate awaiting a teacher response or escalated.
    if ctx.has_open_gate:
        return False

    # 3. Must be soft-deleted and past this data class's retention window.
    #    `is_expired` already returns False when deleted_at is None.
    if not is_expired(ctx.deleted_at, retention_days):
        return False

    # 4. ADR-026 revision/revert window. If this run was ever fast-laned,
    #    it stays protected until export_finalize has materialized AND the
    #    revert window has elapsed since the auto-approval. Ambiguity (fast
    #    lane fired but we can't prove export_finalize happened) fails closed.
    if ctx.fast_lane_approved_at is not None:
        if not ctx.export_finalized:
            return False
        approved_at = ctx.fast_lane_approved_at
        if approved_at.tzinfo is None:
            # Same naive-datetime round-trip caveat as `retention.is_expired`.
            approved_at = approved_at.replace(tzinfo=UTC)
        window_closes_at = approved_at + timedelta(seconds=FAST_LANE_REVERT_WINDOW_SECONDS)
        if now < window_closes_at:
            return False

    return True


async def build_run_prune_context(db: AsyncSession, run: Run) -> RunPruneContext:
    """Gather the DB-backed facts ``is_prunable`` needs for *run*."""
    from sqlalchemy import select

    open_gate_id = (
        await db.execute(
            select(GateInterrupt.gate_id)
            .where(
                GateInterrupt.run_id == run.run_id,
                GateInterrupt.status.in_(_OPEN_GATE_STATUSES),
            )
            .limit(1),
        )
    ).scalar_one_or_none()

    fast_lane_approved_at = (
        await db.execute(
            select(RunEvent.created_at)
            .where(
                RunEvent.run_id == run.run_id,
                RunEvent.event_name == _AUTO_APPROVED_EVENT_NAME,
            )
            .order_by(RunEvent.created_at.desc())
            .limit(1),
        )
    ).scalar_one_or_none()

    export_finalize_row = (
        await db.execute(
            select(RunStatusHistory.id)
            .where(
                RunStatusHistory.run_id == run.run_id,
                RunStatusHistory.stage == _EXPORT_FINALIZE_STAGE,
            )
            .limit(1),
        )
    ).scalar_one_or_none()

    return RunPruneContext(
        run_id=run.run_id,
        status=run.status,
        deleted_at=run.deleted_at,
        has_open_gate=open_gate_id is not None,
        fast_lane_approved_at=fast_lane_approved_at,
        export_finalized=export_finalize_row is not None,
    )
