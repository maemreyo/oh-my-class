"""Measurement for the QA-02 load harness — sourced from the same
`run_events`/`Run`/`RunJob` tables the OPS-03 dashboard and OPS-04 SLO
alerting read (services/gateway/slo_metrics.py), not a parallel metric.

This module only *reads*: it scopes queries to the run_ids the driver
submitted during one load-test invocation, and computes the percentiles/
breakdown a release-gate report needs (p50/p95/p99, not just slo_metrics'
p95; breaker trips; tokens/run) that slo_metrics doesn't already expose.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.gateway.models import Run, RunStatus
from services.gateway.teaching_pack_models import RunEvent, RunJob, RunJobStatus

_TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})
_ACTIVE_JOB_STATUSES = frozenset({RunJobStatus.PENDING, RunJobStatus.QUEUED})


@dataclass(frozen=True, slots=True)
class PerfReport:
    run_ids: tuple[str, ...]
    total_submitted: int
    total_terminal: int
    total_completed: int
    success_rate: float | None
    p50_latency_seconds: float | None
    p95_latency_seconds: float | None
    p99_latency_seconds: float | None
    avg_tokens_per_run: float | None
    total_cost_usd: float
    breaker_trip_count: int
    queue_depth_timeseries: list[int] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "total_submitted": self.total_submitted,
            "total_terminal": self.total_terminal,
            "total_completed": self.total_completed,
            "success_rate": self.success_rate,
            "p50_latency_seconds": self.p50_latency_seconds,
            "p95_latency_seconds": self.p95_latency_seconds,
            "p99_latency_seconds": self.p99_latency_seconds,
            "avg_tokens_per_run": self.avg_tokens_per_run,
            "total_cost_usd": self.total_cost_usd,
            "breaker_trip_count": self.breaker_trip_count,
            "queue_depth_timeseries": self.queue_depth_timeseries,
        }


def percentile(values: list[float], pct: float) -> float | None:
    """pct in [0, 1]. Same nearest-rank method as services/gateway/slo_metrics._p95,
    generalized to any percentile so p50/p99 agree with the dashboard's p95."""
    if not values:
        return None
    ordered = sorted(values)
    index = max(round((len(ordered) * pct) + 0.5) - 1, 0)
    return ordered[min(index, len(ordered) - 1)]


async def sample_queue_depth(session: AsyncSession, run_ids: list[str]) -> int:
    """Pending+queued RunJob count for exactly this load test's runs — the
    same PENDING/QUEUED statuses services/gateway/slo_metrics._queue_depth_by_teacher
    counts, scoped by run_id instead of by teacher so a shared/staging DB with
    other traffic doesn't pollute the measurement."""
    if not run_ids:
        return 0
    result = await session.execute(
        select(func.count(RunJob.job_id)).where(
            RunJob.run_id.in_(run_ids),
            RunJob.status.in_(_ACTIVE_JOB_STATUSES),
        ),
    )
    return int(result.scalar_one())


async def compute_perf_report(
    session: AsyncSession,
    run_ids: list[str],
    *,
    queue_depth_timeseries: list[int] | None = None,
) -> PerfReport:
    if not run_ids:
        return PerfReport(
            run_ids=(),
            total_submitted=0,
            total_terminal=0,
            total_completed=0,
            success_rate=None,
            p50_latency_seconds=None,
            p95_latency_seconds=None,
            p99_latency_seconds=None,
            avg_tokens_per_run=None,
            total_cost_usd=0.0,
            breaker_trip_count=0,
            queue_depth_timeseries=queue_depth_timeseries or [],
        )

    runs = list((await session.execute(select(Run).where(Run.run_id.in_(run_ids)))).scalars())
    terminal_runs = [run for run in runs if run.status in _TERMINAL_STATUSES]
    completed = [run for run in terminal_runs if run.status is RunStatus.COMPLETED]
    latencies = [
        (run.updated_at - run.created_at).total_seconds()
        for run in terminal_runs
        if run.updated_at is not None and run.created_at is not None
    ]
    tokens = [run.tokens_used for run in runs if run.tokens_used]

    breaker_trip_count = int(
        (
            await session.execute(
                select(func.count(RunEvent.id)).where(
                    RunEvent.run_id.in_(run_ids),
                    RunEvent.event_name == "breaker_tripped",
                ),
            )
        ).scalar_one()
    )

    return PerfReport(
        run_ids=tuple(run_ids),
        total_submitted=len(run_ids),
        total_terminal=len(terminal_runs),
        total_completed=len(completed),
        success_rate=None if not terminal_runs else len(completed) / len(terminal_runs),
        p50_latency_seconds=percentile(latencies, 0.50),
        p95_latency_seconds=percentile(latencies, 0.95),
        p99_latency_seconds=percentile(latencies, 0.99),
        avg_tokens_per_run=(sum(tokens) / len(tokens)) if tokens else None,
        total_cost_usd=sum(run.cost_usd for run in runs),
        breaker_trip_count=breaker_trip_count,
        queue_depth_timeseries=queue_depth_timeseries or [],
    )


async def wait_for_terminal_or_timeout(
    session_factory,
    run_ids: list[str],
    *,
    timeout_seconds: float,
    poll_interval_seconds: float,
    on_sample=None,
) -> list[int]:
    """Poll queue depth + terminal status every `poll_interval_seconds` until
    every run_id reaches a terminal Run.status or the timeout elapses.
    Returns the queue-depth timeseries sampled along the way. `on_sample`,
    if given, is called with (elapsed_seconds, queue_depth, terminal_count)
    each tick — the driver uses it to print progress."""
    import time

    timeseries: list[int] = []
    started = time.monotonic()
    async with session_factory() as session:
        while True:
            depth = await sample_queue_depth(session, run_ids)
            timeseries.append(depth)
            result = await session.execute(
                select(func.count(Run.run_id)).where(
                    Run.run_id.in_(run_ids), Run.status.in_(_TERMINAL_STATUSES),
                ),
            )
            terminal_count = int(result.scalar_one())
            elapsed = time.monotonic() - started
            if on_sample is not None:
                on_sample(elapsed, depth, terminal_count)
            if terminal_count >= len(run_ids) or elapsed >= timeout_seconds:
                return timeseries
            import anyio

            await anyio.sleep(poll_interval_seconds)
