"""Hard purge job for expired soft-deleted runs.

Purging permanently removes run rows and all cascade-linked children
(events, snapshots) whose retention window has elapsed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete, select

from services.gateway.models import ClassProfileModel, Run
from services.gateway.teaching_pack_models import RunEvent
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot
from services.gateway.teaching_pack_types import RunId
from services.gateway.retention import RetentionConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_RETENTION = RetentionConfig()

# PII keys that should be redacted from student evidence.
_STUDENT_EVIDENCE_PII_KEYS = frozenset({
    "name", "student_name", "email", "score", "class_id", "student_id",
})


async def purge_expired_runs(db: AsyncSession) -> list[str]:
    """Permanently delete soft-deleted runs past their retention window.

    For each expired run:
      1. Delete events from ``run_events``
      2. Delete snapshots from ``artifact_snapshots``
      3. Delete the run from ``runs``
      4. Emit ``run.purged`` event (best-effort — row is being deleted)

    Returns:
        List of purged run IDs.
    """
    now = datetime.now(UTC)
    # Find soft-deleted runs where deleted_at + retention_days < now.
    # Use run-level retention_days if set, otherwise default.
    statement = select(Run).where(
        Run.deleted_at.isnot(None),
    )
    result = await db.execute(statement)
    all_deleted_runs = result.scalars().all()

    purged_ids: list[str] = []
    for run in all_deleted_runs:
        retention = run.retention_days if run.retention_days is not None else _RETENTION.run_metadata
        expires_at = run.deleted_at + timedelta(days=retention)  # type: ignore[arg-type]
        # Compare timezone-aware or naive consistently
        expires_at_utc = expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at
        if now <= expires_at_utc:
            continue

        typed_run_id = RunId(run.run_id)

        # 1. Delete events
        await db.execute(
            delete(RunEvent).where(RunEvent.run_id == typed_run_id),
        )
        # 2. Delete snapshots
        await db.execute(
            delete(ArtifactSnapshot).where(ArtifactSnapshot.run_id == typed_run_id),
        )
        # 3. Delete run
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
