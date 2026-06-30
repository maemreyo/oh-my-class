---
title: App-level SLOs and alerting
status: done
labels: []
created: 2026-06-30
---

## What to build

Production needs app-level service-level objectives and alerts, beyond container healthchecks + 9Router provider Slack alerts. Reuse the existing Langfuse traces + `TeachingPackJobStore` metrics; no new vendor (Sentry optional later).

- Define SLOs: run success-rate, p95 latency per run/stage, gate-backlog (gates pending past TTL), job-queue depth, cost/day. Per-teacher and global.
- Emit metrics from the durable substrate (job store + run rows + Langfuse), not the in-memory event bus.
- Alerting: breach → Slack/Zalo notification with the offending dimension; thresholds configurable; dedup/cooldown.
- A minimal ops dashboard (or Langfuse views) for the SLOs.

## Acceptance criteria

- [x] SLOs are defined and computed from durable sources (job store + run rows + Langfuse).
- [x] Breaches (success-rate, p95 latency, gate-backlog, queue-depth, cost/day) fire a deduped alert to Slack/Zalo with context.
- [x] Thresholds are configurable; alerting has cooldown to avoid storms.
- [x] Metrics are visible via a dashboard or Langfuse views.
- [x] No reliance on the in-memory event bus for SLO correctness.

## Detailed test suite

(Real DB; deterministic metric computation.)

- [x] `services/gateway/tests/test_slo_metrics.py`: seeded runs produce correct success-rate / p95 / queue-depth / gate-backlog figures.
- [x] `services/gateway/tests/test_alerting.py`: a breach fires exactly one alert (cooldown holds); recovery clears; thresholds are config-driven.
- [x] Run `uv run pytest services/gateway/tests/test_slo_metrics.py services/gateway/tests/test_alerting.py -v`.

## Verification

- `uv run pytest services/gateway/tests/test_slo_metrics.py services/gateway/tests/test_alerting.py services/gateway/tests/test_ops_slo_router.py -q` → 7 passed.
- LSP diagnostics clean for `services/gateway/slo_metrics.py`, `services/gateway/slo_alerting.py`, `services/gateway/routers/ops.py`, `services/gateway/tests/test_slo_metrics.py`, `services/gateway/tests/test_alerting.py`, and `services/gateway/tests/test_ops_slo_router.py`.
- Manual surface QA covered by `services/gateway/tests/test_ops_slo_router.py`, which drives the admin `/ops/slo` endpoint through FastAPI/TestClient and verifies the SLO dashboard payload.

## Blocked by

None - can start immediately
