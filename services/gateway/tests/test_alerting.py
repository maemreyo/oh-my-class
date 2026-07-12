from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx2

from services.gateway.slo_alerting import AlertCooldown, SloBreach, SloThresholds, dispatch_slo_alerts, evaluate_slo_breaches
from services.gateway.slo_alerting import WebhookAlertSink
from services.gateway.teaching_pack_types import JsonObject
from services.gateway.slo_metrics import SloDimension, SloSnapshot


class TestSloAlerting:
    async def test_breach_fires_once_during_cooldown_and_refires_after_recovery(self) -> None:
        sink = RecordingAlertSink()
        cooldown = AlertCooldown()
        thresholds = SloThresholds(min_success_rate=0.95, cooldown_seconds=60)
        now = datetime(2026, 6, 30, 8, tzinfo=UTC)
        failing_snapshot = _snapshot(success_rate=0.5)

        first = await dispatch_slo_alerts(
            failing_snapshot,
            thresholds=thresholds,
            cooldown=cooldown,
            sink=sink,
            now=now,
        )
        second = await dispatch_slo_alerts(
            failing_snapshot,
            thresholds=thresholds,
            cooldown=cooldown,
            sink=sink,
            now=now + timedelta(seconds=30),
        )
        recovered = await dispatch_slo_alerts(
            _snapshot(success_rate=1.0),
            thresholds=thresholds,
            cooldown=cooldown,
            sink=sink,
            now=now + timedelta(seconds=40),
        )
        refired = await dispatch_slo_alerts(
            failing_snapshot,
            thresholds=thresholds,
            cooldown=cooldown,
            sink=sink,
            now=now + timedelta(seconds=50),
        )

        assert len(first) == 1
        assert second == []
        assert recovered == []
        assert len(refired) == 1
        assert [breach.metric for breach in sink.breaches] == ["success_rate", "success_rate"]

    def test_thresholds_are_config_driven_for_each_slo_metric(self) -> None:
        thresholds = SloThresholds(
            min_success_rate=0.9,
            max_run_latency_p95_seconds=30,
            max_gate_backlog=0,
            max_queue_depth=2,
            max_cost_usd_per_day=1,
        )

        breaches = evaluate_slo_breaches(_snapshot(
            success_rate=0.89,
            latency=31,
            gate_backlog=1,
            queue_depth=3,
            cost=1.01,
        ), thresholds)

        assert {breach.metric for breach in breaches} == {
            "success_rate",
            "run_latency_p95_seconds",
            "gate_backlog",
            "queue_depth",
            "cost_usd_today",
        }

    def test_dead_letter_growth_fires_a_page_severity_breach(self) -> None:
        """#124: any dead-lettered job is a page-level signal (ADR-034
        decision 2), distinct from the warn-level breaches on the other
        SLO dimensions."""
        thresholds = SloThresholds(max_dead_letter_count=0)

        snapshot = _snapshot(success_rate=1.0, dead_letter_count=1)
        breaches = evaluate_slo_breaches(snapshot, thresholds)

        dead_letter_breaches = [b for b in breaches if b.metric == "dead_letter_count"]
        assert len(dead_letter_breaches) == 1
        assert dead_letter_breaches[0].severity == "page"
        assert dead_letter_breaches[0].observed == 1

    def test_thresholds_load_from_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("OMC_SLO_MIN_SUCCESS_RATE", "0.8")
        monkeypatch.setenv("OMC_SLO_MAX_RUN_LATENCY_P95_SECONDS", "45")
        monkeypatch.setenv("OMC_SLO_MAX_GATE_BACKLOG", "2")
        monkeypatch.setenv("OMC_SLO_MAX_QUEUE_DEPTH", "5")
        monkeypatch.setenv("OMC_SLO_MAX_DEAD_LETTER_COUNT", "1")
        monkeypatch.setenv("OMC_SLO_MAX_COST_USD_PER_DAY", "3.5")
        monkeypatch.setenv("OMC_SLO_ALERT_COOLDOWN_SECONDS", "30")

        thresholds = SloThresholds.from_env()

        assert thresholds == SloThresholds(
            min_success_rate=0.8,
            max_run_latency_p95_seconds=45,
            max_gate_backlog=2,
            max_queue_depth=5,
            max_dead_letter_count=1,
            max_cost_usd_per_day=3.5,
            cooldown_seconds=30,
        )

    async def test_webhook_sink_posts_slack_zalo_payloads_with_context(self) -> None:
        client = RecordingHttpClient()
        sink = WebhookAlertSink(client=client, urls=("https://slack.test/hook", "https://zalo.test/hook"))
        breach = SloBreach(
            key="teacher:teacher-1:queue_depth",
            dimension="teacher:teacher-1",
            metric="queue_depth",
            observed=7,
            threshold=5,
            teacher_id="teacher-1",
            runbook_path="docs/runbooks/job-queue-stuck.md",
        )

        await sink.send(breach)

        assert [request.url for request in client.requests] == ["https://slack.test/hook", "https://zalo.test/hook"]
        assert all(request.payload["metric"] == "queue_depth" for request in client.requests)
        assert all(request.payload["teacher_id"] == "teacher-1" for request in client.requests)
        assert all(Path(str(request.payload["runbook_path"])).exists() for request in client.requests)


class RecordingAlertSink:
    def __init__(self) -> None:
        self.breaches: list[SloBreach] = []

    async def send(self, breach: SloBreach) -> None:
        self.breaches.append(breach)


class RecordingHttpClient:
    def __init__(self) -> None:
        self.requests: list[RecordedWebhookRequest] = []

    async def post(self, url: str, *, json: JsonObject) -> httpx2.Response:
        self.requests.append(RecordedWebhookRequest(url=url, payload=json))
        return httpx2.Response(202)


class RecordedWebhookRequest:
    def __init__(self, *, url: str, payload: JsonObject) -> None:
        self.url = url
        self.payload = payload


def _snapshot(
    *,
    success_rate: float,
    latency: float | None = None,
    gate_backlog: int = 0,
    queue_depth: int = 0,
    dead_letter_count: int = 0,
    cost: float = 0,
) -> SloSnapshot:
    now = datetime(2026, 6, 30, 8, tzinfo=UTC)
    return SloSnapshot(
        generated_at=now,
        window_started_at=now - timedelta(hours=24),
        global_dimension=SloDimension(
            name="global",
            teacher_id=None,
            run_count=2,
            success_rate=success_rate,
            run_latency_p95_seconds=latency,
            stage_latency_p95_seconds={},
            gate_backlog=gate_backlog,
            queue_depth=queue_depth,
            dead_letter_count=dead_letter_count,
            cost_usd_today=cost,
        ),
    )
