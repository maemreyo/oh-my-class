"""OPS-07 scheduled cleanup: prune + rollup + redact, modeled on the recovery
sweeper (`recovery_sweeper.py` / `main.py::_run_teaching_pack_sweeper`), but
on its own slower (daily) cadence per ADR-034 §5.

Ordering matters for one invariant: KPI rollup must happen *before* the
events it summarizes are deleted (never the reverse). Everything else is
independently safe to reorder since each purge function re-derives its own
eligibility via `prune_policy.is_prunable`.

Dev safety (issue's "env mapping" requirement): ``dry_run=True`` runs every
step for real inside one transaction, then rolls back instead of committing
-- so the *exact* prune logic executes and its would-be effect is
observable/loggable, but nothing is actually deleted. This is deliberately
not two divergent code paths (a "real" purge function and a separate
"simulated" one) that could drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from services.gateway.purge import (
    purge_expired_artifacts,
    purge_expired_class_profiles,
    purge_expired_run_events,
    purge_expired_runs,
    purge_expired_snapshots,
    purge_student_evidence,
)
from services.gateway.retention import RetentionConfig
from services.gateway.run_event_rollup import (
    days_needing_rollup_before_purge,
    ensure_kpi_rollup_for_day,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_RETENTION = RetentionConfig()


@dataclass(frozen=True, slots=True)
class DataLifecycleCleanupResult:
    dry_run: bool
    rolled_up_days: int
    purged_events: int
    purged_snapshots: int
    purged_artifacts: int
    purged_runs: list[str]
    purged_class_profiles: list[str]
    redacted_student_evidence: int


async def run_data_lifecycle_cleanup(
    db: AsyncSession, *, dry_run: bool,
) -> DataLifecycleCleanupResult:
    """Run one full OPS-07 cleanup pass.

    Caller owns the transaction boundary in the sense that this function
    itself decides commit-vs-rollback based on *dry_run* -- callers should
    not additionally commit/rollback the same session afterward.
    """
    days_to_roll_up = await days_needing_rollup_before_purge(
        db, events_retention_days=_RETENTION.events,
    )
    for day in days_to_roll_up:
        await ensure_kpi_rollup_for_day(db, day)

    redacted = await purge_student_evidence(db)
    purged_events = await purge_expired_run_events(db)
    purged_snapshots = await purge_expired_snapshots(db)
    purged_artifacts = await purge_expired_artifacts(db)
    purged_runs = await purge_expired_runs(db)
    purged_class_profiles = await purge_expired_class_profiles(db)

    if dry_run:
        await db.rollback()
    else:
        await db.commit()

    return DataLifecycleCleanupResult(
        dry_run=dry_run,
        rolled_up_days=len(days_to_roll_up),
        purged_events=purged_events,
        purged_snapshots=purged_snapshots,
        purged_artifacts=purged_artifacts,
        purged_runs=purged_runs,
        purged_class_profiles=purged_class_profiles,
        redacted_student_evidence=redacted,
    )
