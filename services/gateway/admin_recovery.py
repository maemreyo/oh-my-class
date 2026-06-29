"""Admin recovery actions for stuck or failed pipeline runs.

Every recovery action emits an audit event via the run_events table
for traceability.  Recovery actions are intentionally limited to safe,
reversible operations — no arbitrary stage jumps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, assert_never

from sqlalchemy import select

from services.gateway.logging_config import get_logger
from services.gateway.models import Run, RunStatus
from services.gateway.notification_db import Notification, NotificationDeliveryRecord
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    TeachingPackEventVisibility,
    RunJob,
    RunJobStatus,
)
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_log = get_logger("admin_recovery")


class SafeRecoveryAction(StrEnum):
    RETRY_STUCK_JOB = "retry_stuck_job"
    RETRY_FAILED_ARTIFACT = "retry_failed_artifact"
    RETRY_NOTIFICATION = "retry_notification"
    CANCEL_RUN = "cancel_run"
    REOPEN_GATE = "reopen_gate"
    MARK_ESCALATED = "mark_escalated"


@dataclass(frozen=True, slots=True)
class AdminRecoveryRequest:
    run_id: str
    action: SafeRecoveryAction
    reason: str
    admin_id: str


@dataclass(frozen=True, slots=True)
class AdminRecoveryResult:
    success: bool
    message: str
    action_performed: str


async def execute_recovery(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Execute a safe admin recovery action with audit trail."""
    _log.info(
        "admin.recovery.requested run_id=%s action=%s admin_id=%s reason=%s",
        request.run_id,
        request.action,
        request.admin_id,
        request.reason,
    )

    match request.action:
        case SafeRecoveryAction.RETRY_STUCK_JOB:
            result = await _retry_stuck_job(request, db)
        case SafeRecoveryAction.RETRY_FAILED_ARTIFACT:
            result = await _retry_failed_artifact(request, db)
        case SafeRecoveryAction.RETRY_NOTIFICATION:
            result = await _retry_notification(request, db)
        case SafeRecoveryAction.CANCEL_RUN:
            result = await _cancel_run(request, db)
        case SafeRecoveryAction.REOPEN_GATE:
            result = await _reopen_gate(request, db)
        case SafeRecoveryAction.MARK_ESCALATED:
            result = await _mark_escalated(request, db)
        case unreachable:
            assert_never(unreachable)

    # Always emit audit event
    await _emit_audit_event(request, result, db)
    await db.flush()

    _log.info(
        "admin.recovery.completed run_id=%s action=%s success=%s",
        request.run_id,
        request.action,
        result.success,
    )
    return result


async def _retry_stuck_job(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Reset a stuck RUNNING job back to PENDING."""
    statement = (
        select(RunJob)
        .where(
            RunJob.run_id == request.run_id,
            RunJob.status == RunJobStatus.RUNNING,
        )
        .order_by(RunJob.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    result = await db.execute(statement)
    job = result.scalar_one_or_none()

    if job is None:
        return AdminRecoveryResult(
            success=False,
            message="No stuck (running) job found for this run",
            action_performed=request.action,
        )

    job.status = RunJobStatus.PENDING
    job.lease_owner = None
    job.lease_expires_at = None
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Job {job.job_id} reset to pending",
        action_performed=request.action,
    )


async def _retry_failed_artifact(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Reset a failed job back to PENDING for retry."""
    statement = (
        select(RunJob)
        .where(
            RunJob.run_id == request.run_id,
            RunJob.status == RunJobStatus.FAILED,
        )
        .order_by(RunJob.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    result = await db.execute(statement)
    job = result.scalar_one_or_none()

    if job is None:
        return AdminRecoveryResult(
            success=False,
            message="No failed job found for this run",
            action_performed=request.action,
        )

    job.status = RunJobStatus.PENDING
    job.lease_owner = None
    job.lease_expires_at = None
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Job {job.job_id} reset to pending for retry",
        action_performed=request.action,
    )


async def _cancel_run(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Set run status to CANCELLED."""
    statement = select(Run).where(Run.run_id == request.run_id).with_for_update()
    result = await db.execute(statement)
    run = result.scalar_one_or_none()

    if run is None:
        return AdminRecoveryResult(
            success=False,
            message=f"Run {request.run_id} not found",
            action_performed=request.action,
        )

    if run.status in (RunStatus.COMPLETED, RunStatus.CANCELLED):
        return AdminRecoveryResult(
            success=False,
            message=f"Run is already {run.status.value}",
            action_performed=request.action,
        )

    run.status = RunStatus.CANCELLED
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Run {request.run_id} cancelled",
        action_performed=request.action,
    )


async def _retry_notification(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    statement = (
        select(NotificationDeliveryRecord)
        .join(Notification, NotificationDeliveryRecord.notification_id == Notification.id)
        .where(
            Notification.run_id == request.run_id,
            NotificationDeliveryRecord.status.in_(["failed", "pending"]),
        )
        .order_by(NotificationDeliveryRecord.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    result = await db.execute(statement)
    delivery = result.scalar_one_or_none()

    if delivery is None:
        return AdminRecoveryResult(
            success=False,
            message="No failed or pending notification delivery found for this run",
            action_performed=request.action,
        )

    delivery.status = "delivered"
    delivery.delivered_at = datetime.now(UTC)
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Notification delivery {delivery.id} marked delivered",
        action_performed=request.action,
    )


async def _reopen_gate(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Reopen the latest active gate interrupt to ACTIVE."""
    statement = (
        select(GateInterrupt)
        .where(
            GateInterrupt.run_id == request.run_id,
            GateInterrupt.status.in_([
                GateInterruptStatus.RESPONDED,
                GateInterruptStatus.EXPIRED,
            ]),
        )
        .order_by(GateInterrupt.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    result = await db.execute(statement)
    gate = result.scalar_one_or_none()

    if gate is None:
        return AdminRecoveryResult(
            success=False,
            message="No responded/expired gate found for this run",
            action_performed=request.action,
        )

    gate.status = GateInterruptStatus.ACTIVE
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Gate {gate.gate_id} reopened to active",
        action_performed=request.action,
    )


async def _mark_escalated(
    request: AdminRecoveryRequest,
    db: AsyncSession,
) -> AdminRecoveryResult:
    """Set the latest active gate to EXPIRED (escalated)."""
    statement = (
        select(GateInterrupt)
        .where(
            GateInterrupt.run_id == request.run_id,
            GateInterrupt.status == GateInterruptStatus.ACTIVE,
        )
        .order_by(GateInterrupt.created_at.desc())
        .limit(1)
        .with_for_update()
    )
    result = await db.execute(statement)
    gate = result.scalar_one_or_none()

    if gate is None:
        return AdminRecoveryResult(
            success=False,
            message="No active gate found for this run",
            action_performed=request.action,
        )

    gate.status = GateInterruptStatus.EXPIRED
    await db.flush()

    return AdminRecoveryResult(
        success=True,
        message=f"Gate {gate.gate_id} marked as escalated",
        action_performed=request.action,
    )


async def _emit_audit_event(
    request: AdminRecoveryRequest,
    result: AdminRecoveryResult,
    db: AsyncSession,
) -> None:
    """Write an audit event to the run_events table."""
    store = TeachingPackRunStore(db)
    await store.write_event(TeachingPackEventCreate(
        run_id=RunId(request.run_id),
        event_name=f"admin.recovery.{request.action}",
        visibility=TeachingPackEventVisibility.ADMIN,
        payload={
            "admin_id": request.admin_id,
            "reason": request.reason,
            "success": result.success,
            "message": result.message,
            "action": request.action,
        },
    ))
