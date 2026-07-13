"""Hard purge job for expired soft-deleted runs (OPS-07).

Generalizes the original single-data-class purge into one per
``RetentionConfig`` data class (``run_metadata``, ``events``, ``snapshots``,
``artifacts``), each gated by the ADR-026-aware ``is_prunable`` predicate
(`services/gateway/prune_policy.py`) so none of them can ever touch a run
that is pending, escalated, or inside its ADR-026 revision/revert window --
regardless of how long ago it was soft-deleted.

Finer-grained data classes (events, snapshots, artifacts) can legitimately
become prunable *before* the run row itself does, since their retention
periods default shorter than ``run_metadata`` (90/180/180 vs 365 days) --
each is checked independently against its own retention window rather than
waiting for the whole run to qualify.

``student_evidence`` keeps its own tighter, independent 30-day rule
(privacy-by-design, ADR-034 §10) -- it purges from *active* runs by
``created_at``, unrelated to soft-delete/prune status.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from services.gateway.models import Artifact, ClassProfileModel, Run
from services.gateway.prune_policy import build_run_prune_context, is_prunable
from services.gateway.retention import RetentionConfig
from services.gateway.teaching_pack_artifact_models import ArtifactWorkflow
from services.gateway.teaching_pack_models import RunEvent
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_RETENTION = RetentionConfig()

# PII keys that should be redacted from student evidence.
_STUDENT_EVIDENCE_PII_KEYS = frozenset({
    "name", "student_name", "email", "score", "class_id", "student_id",
})


async def _prunable_deleted_runs(db: AsyncSession, retention_days: int) -> list[Run]:
    """Soft-deleted runs that pass ``is_prunable`` for *retention_days*.

    Shared by every data-class purge function below so the ADR-026 gating
    logic (open gates, fast-lane revert window, export_finalize) lives in
    exactly one place (`prune_policy.py`), not re-derived per call site.
    """
    result = await db.execute(select(Run).where(Run.deleted_at.isnot(None)))
    eligible: list[Run] = []
    for run in result.scalars().all():
        ctx = await build_run_prune_context(db, run)
        if is_prunable(ctx, retention_days):
            eligible.append(run)
    return eligible


async def purge_expired_run_events(db: AsyncSession) -> int:
    """Delete ``run_events`` rows for runs prunable at the ``events`` retention.

    Deliberately independent of ``purge_expired_runs``: events (90d default)
    typically clear their retention window well before the run row itself
    (365d), so this can shrink ``run_events`` without waiting on the rest of
    the run's data. Callers that also need OPS-07's KPI rollup guarantee
    should call ``ensure_kpi_rollup_for_run`` (`run_event_rollup.py`) first --
    see ``data_lifecycle_cleanup.py`` for the wired ordering.
    """
    deleted = 0
    for run in await _prunable_deleted_runs(db, _RETENTION.events):
        result = await db.execute(delete(RunEvent).where(RunEvent.run_id == RunId(run.run_id)))
        deleted += result.rowcount or 0
    if deleted:
        await db.flush()
    return deleted


async def purge_expired_snapshots(db: AsyncSession) -> int:
    """Delete ``artifact_snapshots`` rows for runs prunable at the ``snapshots`` retention."""
    deleted = 0
    for run in await _prunable_deleted_runs(db, _RETENTION.snapshots):
        result = await db.execute(
            delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == RunId(run.run_id)),
        )
        deleted += result.rowcount or 0
    if deleted:
        await db.flush()
    return deleted


async def purge_expired_artifacts(db: AsyncSession) -> int:
    """Delete ``artifacts``/``artifact_workflows`` rows for runs prunable at
    the ``artifacts`` retention.

    ``Artifact.run_id`` and ``ArtifactWorkflow.run_id`` are plain string
    columns (no ``ForeignKey``/cascade from ``runs``), so without this these
    rows would be orphaned forever once ``purge_expired_runs`` deletes the
    parent run.
    """
    deleted = 0
    for run in await _prunable_deleted_runs(db, _RETENTION.artifacts):
        result = await db.execute(delete(Artifact).where(Artifact.run_id == run.run_id))
        deleted += result.rowcount or 0
        await db.execute(delete(ArtifactWorkflow).where(ArtifactWorkflow.run_id == run.run_id))
    if deleted:
        await db.flush()
    return deleted


async def purge_expired_runs(db: AsyncSession) -> list[str]:
    """Permanently delete soft-deleted runs past their ``run_metadata`` retention.

    For each run that ``is_prunable`` clears (terminal, no open/escalated
    gate, past retention, outside its ADR-026 revert window):
      1. Delete events from ``run_events``
      2. Delete snapshots from ``artifact_snapshots``
      3. Delete rows from ``artifacts`` / ``artifact_workflows``
      4. Delete the run from ``runs``

    Returns:
        List of purged run IDs.
    """
    result = await db.execute(select(Run).where(Run.deleted_at.isnot(None)))
    purged_ids: list[str] = []
    for run in result.scalars().all():
        retention = (
            run.retention_days if run.retention_days is not None else _RETENTION.run_metadata
        )
        ctx = await build_run_prune_context(db, run)
        if not is_prunable(ctx, retention):
            continue

        typed_run_id = RunId(run.run_id)
        await db.execute(delete(RunEvent).where(RunEvent.run_id == typed_run_id))
        await db.execute(delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == typed_run_id))
        await db.execute(delete(Artifact).where(Artifact.run_id == run.run_id))
        await db.execute(delete(ArtifactWorkflow).where(ArtifactWorkflow.run_id == run.run_id))
        await db.delete(run)
        purged_ids.append(run.run_id)

    await db.flush()
    return purged_ids


async def purge_student_evidence(db: AsyncSession) -> int:
    """Redact student evidence from runs older than the evidence retention window.

    Finds runs where ``class_info`` contains ``student_evidence`` and the
    run's ``created_at`` is older than the student evidence retention
    period.  PII keys are removed from the evidence dict.

    Returns:
        Number of runs whose student evidence was redacted.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=_RETENTION.student_evidence)

    statement = select(Run).where(
        Run.created_at < cutoff.replace(tzinfo=None),
    )
    result = await db.execute(statement)
    runs = result.scalars().all()

    redacted = 0
    for run in runs:
        if not isinstance(run.class_info, dict):
            continue
        evidence = run.class_info.get("student_evidence")
        if not isinstance(evidence, dict):
            continue
        cleaned = {
            k: v for k, v in evidence.items() if k not in _STUDENT_EVIDENCE_PII_KEYS
        }
        if cleaned == evidence:
            continue
        run.class_info = {**run.class_info, "student_evidence": cleaned}
        redacted += 1

    if redacted:
        await db.flush()
    return redacted


async def purge_expired_class_profiles(db: AsyncSession) -> list[str]:
    now = datetime.now(UTC)
    statement = select(ClassProfileModel).where(ClassProfileModel.deleted_at.isnot(None))
    result = await db.execute(statement)
    profiles = result.scalars().all()

    purged_ids: list[str] = []
    for profile in profiles:
        retention = profile.retention_days or _RETENTION.class_profiles
        expires_at = profile.deleted_at + timedelta(days=retention)
        expires_at_utc = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        if now <= expires_at_utc:
            continue
        await db.delete(profile)
        purged_ids.append(profile.class_profile_id)

    await db.flush()
    return purged_ids
