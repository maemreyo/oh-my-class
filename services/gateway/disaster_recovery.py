from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.models import Run
from services.gateway.teaching_pack_models import GateInterrupt, GateInterruptStatus, RunJob, RunStatusHistory


@dataclass(frozen=True, slots=True)
class RestoreDrillSnapshot:
    run_id: str
    run_exists: bool
    active_gate_count: int
    job_count: int
    status_history_count: int


async def collect_restore_drill_snapshot(session: AsyncSession, run_id: str) -> RestoreDrillSnapshot:
    run_exists = await session.get(Run, run_id) is not None
    active_gate_count = await _count_active_gates(session, run_id)
    job_count = await _count_rows(session, select(func.count(RunJob.job_id)).where(RunJob.run_id == run_id))
    status_history_count = await _count_rows(
        session,
        select(func.count(RunStatusHistory.id)).where(RunStatusHistory.run_id == run_id),
    )
    return RestoreDrillSnapshot(
        run_id=run_id,
        run_exists=run_exists,
        active_gate_count=active_gate_count,
        job_count=job_count,
        status_history_count=status_history_count,
    )


async def _count_active_gates(session: AsyncSession, run_id: str) -> int:
    return await _count_rows(
        session,
        select(func.count(GateInterrupt.gate_id)).where(
            GateInterrupt.run_id == run_id,
            GateInterrupt.status == GateInterruptStatus.ACTIVE,
        ),
    )


async def _count_rows(session: AsyncSession, statement) -> int:
    return int((await session.execute(statement)).scalar_one())
