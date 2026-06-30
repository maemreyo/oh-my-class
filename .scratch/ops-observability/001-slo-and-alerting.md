---
title: App-level SLOs and alerting
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Production needs app-level service-level objectives and alerts, beyond container healthchecks + 9Router provider Slack alerts. Reuse the existing Langfuse traces + `TeachingPackJobStore` metrics; no new vendor (Sentry optional later).

- Define SLOs: run success-rate, p95 latency per run/stage, gate-backlog (gates pending past TTL), job-queue depth, cost/day. Per-teacher and global.
- Emit metrics from the durable substrate (job store + run rows + Langfuse), not the in-memory event bus.
- Alerting: breach → Slack/Zalo notification with the offending dimension; thresholds configurable; dedup/cooldown.
- A minimal ops dashboard (or Langfuse views) for the SLOs.

## Acceptance criteria

- [ ] SLOs are defined and computed from durable sources (job store + run rows + Langfuse).
- [ ] Breaches (success-rate, p95 latency, gate-backlog, queue-depth, cost/day) fire a deduped alert to Slack/Zalo with context.
- [ ] Thresholds are configurable; alerting has cooldown to avoid storms.
- [ ] Metrics are visible via a dashboard or Langfuse views.
- [ ] No reliance on the in-memory event bus for SLO correctness.

## Detailed test suite

(Real DB; deterministic metric computation.)

- [ ] `services/gateway/tests/test_slo_metrics.py`: seeded runs produce correct success-rate / p95 / queue-depth / gate-backlog figures.
- [ ] `services/gateway/tests/test_alerting.py`: a breach fires exactly one alert (cooldown holds); recovery clears; thresholds are config-driven.
- [ ] Run `uv run pytest services/gateway/tests/test_slo_metrics.py services/gateway/tests/test_alerting.py -v`.

## Blocked by

None - can start immediately
