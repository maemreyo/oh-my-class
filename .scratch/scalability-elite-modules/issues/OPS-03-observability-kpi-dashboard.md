# [OPS-03] Observability KPI dashboard — Langfuse per-run tracing + a thin `run_events` KPI dashboard

Status: TODO
Labels: ops, observability
ADR: 034
Depends on: none

## Context

Per ADR-034 §2, observability is the ops backbone: we cannot operate the mid-scale SLOs (99.5% success, p95 < 8 min) without seeing them. The pieces exist but are not assembled into an operator-facing dashboard:

- **Per-run tracing (Langfuse)** is deployed and wired: `services/gateway/observability/langfuse_config.py` (`get_langfuse_config` :9, enabled iff `LANGFUSE_PUBLIC_KEY` set), tracing context managers in `services/gateway/observability/tracing.py` and the v4 client in `packages/agents/observability/tracing.py` (`trace_node`, `trace_llm_call`, degrade to `NoOpTrace` when unconfigured). Langfuse runs in `infra/compose/docker-compose.yml` (with MinIO-backed S3 event/media upload).
- **`run_events`** is the durable event spine: `RunEvent` table (`services/gateway/teaching_pack_models.py:204`, `event_name` :218, `stage`, `visibility`, `payload`, `created_at` :224). Events are written from the worker (`_persist_observability_events`, `services/gateway/teaching_pack_worker.py:228`) and typed in `packages/agents/events.py` (`ObservabilityEventType` :23 — includes `breaker_tripped`, `escalate`, `healing_decision`, `gate_decision`, `stage_transition`, `cost_accrued`, etc.).
- **A partial SLO snapshot already exists**: `services/gateway/slo_metrics.py` (`compute_slo_snapshot` :45) + `GET /ops/slo` (`services/gateway/routers/ops.py`, admin-only via `require_admin`). It computes success_rate, run p95, queue_depth, gate_backlog, cost/day — per-teacher and global. But `stage_latency_p95_seconds` is empty (`{}` :104) and several ADR-034 KPIs are missing (escalate/day, healing distribution, fast-lane rate, breaker trips, tokens/run).

The gap is a **thin KPI layer over `run_events`** that surfaces the full ADR-034 §2 KPI set for operators — as SQL views (Grafana-friendly) and/or an extension of the existing `/ops/slo` endpoint — plus confirming Langfuse per-run tracing is the drill-down. OPS-03 is the data/dashboard layer; OPS-04 turns these KPIs into SLO objects + alerts.

## Scope

- [ ] **KPI catalog over `run_events`** — define and expose the ADR-034 §2 KPI set, each sourced from `run_events` and/or `runs`/`run_jobs`:
  - success rate vs 99.5% (already in `slo_metrics`)
  - p95 pack **and per-stage p95** (per-stage depends on OPS-02 populating stage latency; wire the field either way)
  - queue depth (`RunJobStatus.PENDING|QUEUED` count — already in `slo_metrics._queue_depth_by_teacher`)
  - escalations/day (`escalate` events)
  - healing-strategy distribution (`healing_decision` events → retry/rewrite/reroute/replan/escalate counts)
  - fast-lane auto-approve rate (from the ADR-026 audit signal — `gate_decision`/`teacher_audit_log`; auto vs manual)
  - breaker trips (`breaker_tripped` events, split provider-scope vs run-scope)
  - tokens/run (`cost_accrued`/usage; align with `budget.py` accounting)
- [ ] **SQL views** — create read-only SQL views (or materialized views) over `run_events` for each KPI so Grafana (or any BI) can chart them without app code. Keep them additive; do not alter `run_events` write path. Include a per-day time bucket.
- [ ] **Extend `/ops/slo`** — add the missing KPIs to `SloSnapshot`/`SloDimension` (escalate/day, healing distribution, fast-lane rate, breaker trips, tokens/run) so the existing admin endpoint returns the full catalog. Keep it `require_admin`-gated.
- [ ] **Langfuse = drill-down** — confirm per-run traces are the operator's per-run drill-down from a KPI anomaly (trace `session_id = run_id`, per-node spans, LLM generations). Document the KPI→trace path. Ensure tracing stays a no-op degrade when unconfigured (dev) — it already does.
- [ ] **Thin dashboard** — ship a single operator dashboard (Grafana JSON or an equivalent thin panel) presenting the KPI catalog with the SLO thresholds drawn (99.5% line, 8-min line). This is the "thin dashboard" from ADR-034 — not a bespoke UI.
- [ ] **Env mapping** — dev: Langfuse optional/no-op, `/ops/slo` works against local Postgres, dashboard optional. staging/prod: Langfuse enabled, views created via migration, dashboard deployed.
- [ ] **PII discipline** — KPI views and traces must NOT surface `student_evidence`/PII (privacy-by-design, ADR-034 §10). KPIs are aggregate counts/latencies; do not join through to student data. Langfuse metadata already uses `run_id`/`agent`/`step`/`teacher_id` only (`get_trace_metadata`).

## Acceptance

- `/ops/slo` returns the full ADR-034 §2 KPI catalog (success rate, run + per-stage p95, queue depth, escalate/day, healing distribution, fast-lane rate, breaker trips, tokens/run), per-teacher and global, admin-gated.
- SQL views exist for each KPI and a Grafana dashboard renders them with the 99.5% and 8-min thresholds drawn.
- From a KPI anomaly an operator can open the corresponding Langfuse run trace (documented KPI→trace path).
- No KPI surface exposes student PII; dev runs with Langfuse disabled and the endpoint/views still function against local Postgres.
- KPIs are computed from real `run_events` produced by real runs (no fabricated event fixtures for the acceptance check).

## References

- `services/gateway/slo_metrics.py` — `compute_slo_snapshot` :45, `SloDimension` :14 (empty `stage_latency_p95_seconds` :104), `_queue_depth_by_teacher` :111, `_gate_backlog_by_teacher` :121, `_cost_today_by_teacher` :135, `_p95` :145.
- `services/gateway/routers/ops.py` — `GET /ops/slo`, `require_admin`.
- `services/gateway/teaching_pack_models.py` — `RunEvent` :204 (`event_name` :218, `stage`, `visibility`, `payload`, `created_at` :224), `TeachingPackEventVisibility` :69, `ix_run_jobs_status_created_at` :231.
- `packages/agents/events.py` — `ObservabilityEventType` :23 (all KPI-source event types), `emit_run_event` :71.
- `services/gateway/observability_events.py` — `observability_event_row` (how events become `RunEvent` rows).
- `services/gateway/teaching_pack_worker.py:228` — `_persist_observability_events` (write path; visibility split teacher vs internal :238).
- `services/gateway/observability/langfuse_config.py` — `get_langfuse_config` :9, `get_trace_metadata` :27; `packages/agents/observability/tracing.py` — `trace_node`, `trace_llm_call`, `NoOpTrace`.
- `infra/compose/docker-compose.yml` — Langfuse + MinIO services.
- ADR-034 §2; ADR-026 (fast-lane audit signal for the fast-lane-rate KPI).

## Implementation notes

- Prefer **DB views over app-side aggregation** for the KPI catalog — it keeps Grafana self-serve and avoids duplicating percentile logic. Where the endpoint needs the same numbers, have `slo_metrics` query the views so there is one source of truth.
- The existing `_p95` (`slo_metrics.py:145`) and the OPS-02 stage-latency work should share the percentile definition; do not introduce a second p95 formula in SQL that disagrees with Python.
- healing-strategy distribution comes from `healing_decision` event payloads (the orchestrator emits via `_emit_healing_events`; strategies are retry/rewrite/reroute/replan/escalate per `packages/agents/healing/orchestrator.py`). Confirm the payload carries the chosen strategy name.
- breaker-trip KPI must distinguish `scope=provider` (ops-critical, OPS-04 page) from `scope=run` (expected healing noise) using the `scope`/`breaker_key` in the `breaker_tripped` payload (`circuit_breaker.py:204`).
- Keep views/migrations additive and reversible (expand-only), so OPS-08's expand-contract deploy story holds.
- This issue produces the *signals*; OPS-04 consumes them as SLO objects + alerts. Do not build alerting here — just make every KPI queryable and charted.
