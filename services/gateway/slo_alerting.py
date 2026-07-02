from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
import socket
from typing import Final, Protocol

import httpx2

from services.gateway.slo_metrics import SloDimension, SloSnapshot
from services.gateway.teaching_pack_types import JsonObject


_LIMITS: Final = httpx2.Limits(max_connections=200, max_keepalive_connections=40, keepalive_expiry=30.0)
_TIMEOUT: Final = httpx2.Timeout(connect=5.0, read=30.0, write=10.0, pool=10.0)
_SOCKET_OPTIONS: Final = [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]


@dataclass(frozen=True, slots=True)
class SloThresholds:
    min_success_rate: float = 0.95
    max_run_latency_p95_seconds: float = 900.0
    max_gate_backlog: int = 0
    max_queue_depth: int = 25
    max_cost_usd_per_day: float = 10.0
    cooldown_seconds: int = 900

    @classmethod
    def from_env(cls) -> SloThresholds:
        return cls(
            min_success_rate=_float_env("OMC_SLO_MIN_SUCCESS_RATE", cls.min_success_rate),
            max_run_latency_p95_seconds=_float_env(
                "OMC_SLO_MAX_RUN_LATENCY_P95_SECONDS",
                cls.max_run_latency_p95_seconds,
            ),
            max_gate_backlog=_int_env("OMC_SLO_MAX_GATE_BACKLOG", cls.max_gate_backlog),
            max_queue_depth=_int_env("OMC_SLO_MAX_QUEUE_DEPTH", cls.max_queue_depth),
            max_cost_usd_per_day=_float_env("OMC_SLO_MAX_COST_USD_PER_DAY", cls.max_cost_usd_per_day),
            cooldown_seconds=_int_env("OMC_SLO_ALERT_COOLDOWN_SECONDS", cls.cooldown_seconds),
        )


@dataclass(frozen=True, slots=True)
class SloBreach:
    key: str
    dimension: str
    metric: str
    observed: float
    threshold: float
    teacher_id: str | None
    runbook_path: str


class AlertSink(Protocol):
    async def send(self, breach: SloBreach) -> None: ...


class HttpAlertClient(Protocol):
    async def post(self, url: str, *, json: JsonObject) -> httpx2.Response: ...


@dataclass(frozen=True, slots=True)
class WebhookAlertSink:
    client: HttpAlertClient
    urls: tuple[str, ...]

    async def send(self, breach: SloBreach) -> None:
        payload = _webhook_payload(breach)
        for url in self.urls:
            await self.client.post(url, json=payload)


class AlertCooldown:
    def __init__(self) -> None:
        self._sent_at: dict[str, datetime] = {}

    def should_send(self, breach: SloBreach, *, now: datetime, cooldown: timedelta) -> bool:
        previous = self._sent_at.get(breach.key)
        if previous is not None and now - previous < cooldown:
            return False
        self._sent_at[breach.key] = now
        return True

    def clear_recovered(self, active_keys: set[str]) -> None:
        self._sent_at = {key: sent_at for key, sent_at in self._sent_at.items() if key in active_keys}


async def dispatch_slo_alerts(
    snapshot: SloSnapshot,
    *,
    thresholds: SloThresholds,
    cooldown: AlertCooldown,
    sink: AlertSink,
    now: datetime | None = None,
) -> list[SloBreach]:
    generated_at = now or datetime.now(UTC)
    breaches = evaluate_slo_breaches(snapshot, thresholds)
    cooldown.clear_recovered({breach.key for breach in breaches})
    sent: list[SloBreach] = []
    cooldown_period = timedelta(seconds=thresholds.cooldown_seconds)
    for breach in breaches:
        if cooldown.should_send(breach, now=generated_at, cooldown=cooldown_period):
            await sink.send(breach)
            sent.append(breach)
    return sent


def evaluate_slo_breaches(snapshot: SloSnapshot, thresholds: SloThresholds) -> list[SloBreach]:
    dimensions = [snapshot.global_dimension, *snapshot.teachers.values()]
    breaches: list[SloBreach] = []
    for dimension in dimensions:
        breaches.extend(_dimension_breaches(dimension, thresholds))
    return breaches


def _dimension_breaches(dimension: SloDimension, thresholds: SloThresholds) -> list[SloBreach]:
    breaches: list[SloBreach] = []
    if dimension.success_rate is not None and dimension.success_rate < thresholds.min_success_rate:
        breaches.append(_breach(dimension, "success_rate", dimension.success_rate, thresholds.min_success_rate))
    if (
        dimension.run_latency_p95_seconds is not None
        and dimension.run_latency_p95_seconds > thresholds.max_run_latency_p95_seconds
    ):
        breaches.append(_breach(
            dimension,
            "run_latency_p95_seconds",
            dimension.run_latency_p95_seconds,
            thresholds.max_run_latency_p95_seconds,
        ))
    if dimension.gate_backlog > thresholds.max_gate_backlog:
        breaches.append(_breach(dimension, "gate_backlog", dimension.gate_backlog, thresholds.max_gate_backlog))
    if dimension.queue_depth > thresholds.max_queue_depth:
        breaches.append(_breach(dimension, "queue_depth", dimension.queue_depth, thresholds.max_queue_depth))
    if dimension.cost_usd_today > thresholds.max_cost_usd_per_day:
        breaches.append(_breach(dimension, "cost_usd_today", dimension.cost_usd_today, thresholds.max_cost_usd_per_day))
    return breaches


def _breach(dimension: SloDimension, metric: str, observed: float, threshold: float) -> SloBreach:
    return SloBreach(
        key=f"{dimension.name}:{metric}",
        dimension=dimension.name,
        metric=metric,
        observed=observed,
        threshold=threshold,
        teacher_id=dimension.teacher_id,
        runbook_path=_runbook_path(metric),
    )


def _runbook_path(metric: str) -> str:
    match metric:
        case "success_rate" | "cost_usd_today":
            return "docs/runbooks/provider-down.md"
        case "run_latency_p95_seconds":
            return "docs/runbooks/render-pool-crash.md"
        case "gate_backlog":
            return "docs/runbooks/gate-timeout.md"
        case "queue_depth":
            return "docs/runbooks/job-queue-stuck.md"
        case _:
            return "docs/runbooks/provider-down.md"


def configured_webhook_urls() -> tuple[str, ...]:
    return tuple(
        url
        for url in (os.getenv("OMC_SLO_SLACK_WEBHOOK_URL"), os.getenv("OMC_SLO_ZALO_WEBHOOK_URL"))
        if url
    )


def create_alert_http_client() -> httpx2.AsyncClient:
    transport = httpx2.AsyncHTTPTransport(http2=True, retries=3, limits=_LIMITS, socket_options=_SOCKET_OPTIONS)
    return httpx2.AsyncClient(transport=transport, timeout=_TIMEOUT, follow_redirects=True)


def _webhook_payload(breach: SloBreach) -> JsonObject:
    return {
        "text": (
            f"oh-my-class SLO breach: {breach.metric} on {breach.dimension} "
            f"observed={breach.observed} threshold={breach.threshold}"
        ),
        "dimension": breach.dimension,
        "metric": breach.metric,
        "observed": breach.observed,
        "threshold": breach.threshold,
        "teacher_id": breach.teacher_id,
        "runbook_path": breach.runbook_path,
    }


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)
