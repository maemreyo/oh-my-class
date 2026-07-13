"""Daily KPI rollup for ``run_events`` (OPS-07).

ADR-034 §5 requires ``run_events`` to be prunable/partition-droppable
without losing the OPS-03 dashboard's KPIs (success rate, p95, escalate
count, healing distribution, breaker trips, tokens). Rather than invent a
new aggregation, this reuses the exact terminal-status/p95 logic
`slo_metrics.py` already computes live from ``Run`` rows
(`services/gateway/slo_metrics.py:90-108`) and adds the event-derived counts
that module doesn't cover (escalate/breaker/healing/tokens come from
``run_events``, not ``runs``).

The one invariant OPS-07 cares about: ``ensure_kpi_rollup_for_day`` must be
called -- and succeed -- *before* any code deletes/drops the events for that
day. ``purge_expired_run_events`` does not call this itself (it doesn't know
which days it's about to touch are ready); ``data_lifecycle_cleanup.py``
wires the ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, Float, Integer, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Mapped, mapped_column

from services.gateway.models import Base, Run, RunStatus, utc_now
from services.gateway.slo_metrics import (
    _p95,  # noqa: PLC2701 -- reuse, don't reinvent (see module docstring)
)
from services.gateway.teaching_pack_models import RunEvent

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

_TERMINAL_STATUSES = frozenset({RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED})

# event_name values that carry the counts OPS-03 wants; see
# `services/gateway/observability_events.py` and
# `services/gateway/teaching_pack_completion.py` for where each is emitted.
_SUCCESS_EVENT = "teaching_pack.run.completed"
_FAIL_EVENT = "teaching_pack.run.failed"
_ESCALATE_EVENT = "escalate"
_BREAKER_TRIPPED_EVENT = "breaker_tripped"
_HEALING_EVENT = "healing_decision"
_COST_EVENT = "cost_accrued"


class RunEventKpiRollup(Base):
    """One row per UTC day -- the rolled-up shape OPS-03 unions with live events."""

    __tablename__ = "run_event_kpi_rollups"
    __table_args__ = {"schema": "public"}

    day: Mapped[date] = mapped_column(Date, primary_key=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    escalate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    breaker_trip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    healing_distribution: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False, default=dict)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    run_latency_p95_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now,
    )


@dataclass(frozen=True, slots=True)
class DailyKpiRollup:
    day: date
    event_count: int
    success_count: int
    fail_count: int
    escalate_count: int
    breaker_trip_count: int
    healing_distribution: dict[str, int]
    tokens_used: int
    run_latency_p95_seconds: float | None

    @property
    def success_rate(self) -> float | None:
        terminal = self.success_count + self.fail_count
        return None if terminal == 0 else self.success_count / terminal


def _inner_payload(payload: object) -> dict[str, Any]:
    """Agent-observability events nest their real payload one level deeper
    (`observability_event_payload`, `services/gateway/observability_events.py`)
    than events written directly by `teaching_pack_completion.py`. Unwrap
    defensively either way."""
    if isinstance(payload, dict) and "observability_event_type" in payload:
        inner = payload.get("payload")
        return inner if isinstance(inner, dict) else {}
    return payload if isinstance(payload, dict) else {}


async def compute_daily_kpi_rollup(db: AsyncSession, day: date) -> DailyKpiRollup:
    """Aggregate ``run_events`` (and ``runs`` for latency) for one UTC day.

    Pure aggregation -- does not write anything. Callers persist via
    ``ensure_kpi_rollup_for_day``.
    """
    day_start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    rows = list((
        await db.execute(
            select(RunEvent.event_name, RunEvent.payload).where(
                RunEvent.created_at >= day_start,
                RunEvent.created_at < day_end,
            ),
        )
    ).all())

    success_count = 0
    fail_count = 0
    escalate_count = 0
    breaker_trip_count = 0
    healing_distribution: dict[str, int] = {}
    tokens_used = 0

    for event_name, payload in rows:
        if event_name == _SUCCESS_EVENT:
            success_count += 1
        elif event_name == _FAIL_EVENT:
            fail_count += 1
        elif event_name == _ESCALATE_EVENT:
            escalate_count += 1
        elif event_name == _BREAKER_TRIPPED_EVENT:
            breaker_trip_count += 1
        elif event_name == _HEALING_EVENT:
            strategy = str(_inner_payload(payload).get("healing_strategy", "unknown"))
            healing_distribution[strategy] = healing_distribution.get(strategy, 0) + 1
        elif event_name == _COST_EVENT:
            inner = _inner_payload(payload)
            prompt_tokens = int(inner.get("prompt_tokens", 0) or 0)
            completion_tokens = int(inner.get("completion_tokens", 0) or 0)
            tokens_used += prompt_tokens + completion_tokens

    terminal_runs = list((
        await db.execute(
            select(Run.created_at, Run.updated_at, Run.status).where(
                Run.updated_at >= day_start,
                Run.updated_at < day_end,
                Run.status.in_(_TERMINAL_STATUSES),
            ),
        )
    ).all())
    latencies = [
        (updated_at - created_at).total_seconds()
        for created_at, updated_at, _status in terminal_runs
        if created_at is not None and updated_at is not None
    ]

    return DailyKpiRollup(
        day=day,
        event_count=len(rows),
        success_count=success_count,
        fail_count=fail_count,
        escalate_count=escalate_count,
        breaker_trip_count=breaker_trip_count,
        healing_distribution=healing_distribution,
        tokens_used=tokens_used,
        run_latency_p95_seconds=_p95(latencies),
    )


async def ensure_kpi_rollup_for_day(db: AsyncSession, day: date) -> RunEventKpiRollup:
    """Idempotent upsert -- safe to call repeatedly (e.g. once per cleanup run
    while the day is still "recent", then a final call right before that
    day's events are purged/partition-dropped)."""
    rollup = await compute_daily_kpi_rollup(db, day)
    statement = pg_insert(RunEventKpiRollup).values(
        day=rollup.day,
        event_count=rollup.event_count,
        success_count=rollup.success_count,
        fail_count=rollup.fail_count,
        escalate_count=rollup.escalate_count,
        breaker_trip_count=rollup.breaker_trip_count,
        healing_distribution=rollup.healing_distribution,
        tokens_used=rollup.tokens_used,
        run_latency_p95_seconds=rollup.run_latency_p95_seconds,
    )
    statement = statement.on_conflict_do_update(
        index_elements=["day"],
        set_={
            "event_count": statement.excluded.event_count,
            "success_count": statement.excluded.success_count,
            "fail_count": statement.excluded.fail_count,
            "escalate_count": statement.excluded.escalate_count,
            "breaker_trip_count": statement.excluded.breaker_trip_count,
            "healing_distribution": statement.excluded.healing_distribution,
            "tokens_used": statement.excluded.tokens_used,
            "run_latency_p95_seconds": statement.excluded.run_latency_p95_seconds,
            "computed_at": utc_now(),
        },
    )
    await db.execute(statement)
    await db.flush()
    result = await db.execute(select(RunEventKpiRollup).where(RunEventKpiRollup.day == day))
    return result.scalar_one()


async def days_needing_rollup_before_purge(
    db: AsyncSession, *, events_retention_days: int,
) -> list[date]:
    """Distinct UTC days among ``run_events`` old enough to be purge
    candidates (i.e. their parent run could plausibly become prunable), so a
    cleanup job knows exactly which days to roll up before deleting.

    Fail-closed by construction: this only *widens* the set of days rolled
    up (a day rolled up but never actually purged is harmless), never
    narrows it -- there is no path here that skips a day purge will touch.
    """
    cutoff = datetime.now(UTC) - timedelta(days=events_retention_days)
    result = await db.execute(
        select(func.distinct(cast(RunEvent.created_at, Date))).where(RunEvent.created_at < cutoff),
    )
    return sorted(row[0] for row in result.all())
