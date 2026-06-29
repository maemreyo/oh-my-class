from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import assert_never

from sqlalchemy import select

from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_models import (
    GateInterrupt,
    GateInterruptStatus,
    RunJob,
    RunJobStatus,
)

ACTIVE_ADMIN_RUN_STATUSES = (
    RunStatus.PENDING,
    RunStatus.PLANNING,
    RunStatus.RESEARCHING,
    RunStatus.GENERATING,
    RunStatus.REVIEWING,
    RunStatus.AWAITING_APPROVAL,
    RunStatus.EXPORTING,
)


class AdminRunOperationalFilter(StrEnum):
    FAILED = "failed"
    STUCK = "stuck"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"
    AWAITING_GATE = "awaiting_gate"


def apply_operational_filter(statement, operational_filter: AdminRunOperationalFilter):
    match operational_filter:
        case AdminRunOperationalFilter.FAILED:
            return statement.where(Run.status == RunStatus.FAILED)
        case AdminRunOperationalFilter.STUCK:
            return statement.where(Run.run_id.in_(
                select(RunJob.run_id).where(
                    RunJob.status == RunJobStatus.RUNNING,
                    RunJob.lease_expires_at.is_not(None),
                    RunJob.lease_expires_at <= datetime.now(UTC),
                ),
            ))
        case AdminRunOperationalFilter.ESCALATED | AdminRunOperationalFilter.TIMED_OUT:
            return statement.where(Run.run_id.in_(
                select(GateInterrupt.run_id).where(
                    GateInterrupt.status == GateInterruptStatus.EXPIRED,
                ),
            ))
        case AdminRunOperationalFilter.AWAITING_GATE:
            return statement.where(Run.status.in_(ACTIVE_ADMIN_RUN_STATUSES)).where(
                Run.run_id.in_(
                    select(GateInterrupt.run_id).where(
                        GateInterrupt.status == GateInterruptStatus.ACTIVE,
                    ),
                ),
            )
        case unreachable:
            assert_never(unreachable)
