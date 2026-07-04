# [OPS-04] SLO objects + tiered alerting (page vs warn), ops alerts separate from teacher escalations

Status: TODO
Labels: ops, observability, alerting
ADR: 034
Depends on: OPS-03

## Context

OPS-03 makes every ADR-034 §2 KPI queryable/charted. OPS-04 turns those KPIs into **first-class SLO objects with error budgets** and a **tiered alerting** policy, per ADR-034 §2. Today `slo_metrics.compute_slo_snapshot` produces a point-in-time snapshot but there is no SLO *object* (target + error budget + burn), and no alerting — the numbers exist, nobody gets paged.

The alerting must respect an existing, deliberate separation: **teacher notifications ≠ ops alerts.** `services/gateway/notifications.py` (`notify_run_failed` :177, `notify_run_escalated` :199, `notify_gate_required` :53, etc.) is the *teacher*-facing channel, backed by `notification_store.py`/`notification_models.py`. Ops alerts (a provider breaker opening, the DLQ growing, the queue not draining) must go to an **operator** channel, never merged into a teacher's escalation notices. ADR-034 §2 states this explicitly.

Tiering (from ADR-034 §2):
- **PAGE (urgent, human now):** success rate < 99.5%; a provider circuit breaker open; dead-letter queue growing; queue not draining.
- **WARN (attention, not urgent):** p95 > 8 min; queue growing (but draining); escalation spike; healing-strategy skew (e.g. sudden reroute/replan/escalate surge indicating systemic degradation).

## Scope

- [ ] **SLO objects with error budgets** — define SLO objects (target + window + error budget + burn rate) for at least: run-success ≥ 99.5%, p95 pack < 8 min, per-stage p95 (from OPS-02), queue-drain health, DLQ health. Model them as config + evaluator (mirror the pure-config style of `budget.py`/`slo_metrics`), computed over the OPS-03 KPI views. Each SLO reports remaining error budget and current burn.
- [ ] **Tiered alert policy** — implement the page-vs-warn mapping above as a policy object that evaluates SLO/KPI state and emits alerts at the right tier. Thresholds env-tunable.
  - PAGE: success < 99.5% (error-budget burn), provider `breaker_tripped` (scope=provider), DLQ growth (OPS-11 dead-letter count rising), queue not draining (pending/queued count non-decreasing over N sweeps).
  - WARN: p95 > 8 min, queue growing but draining, escalate/day spike, healing-strategy skew.
- [ ] **Ops alert channel, separate from teacher notifications** — route ops alerts to an operator sink distinct from `notifications.py` teacher channel. Reuse the notification *infrastructure* pattern (store/model/sink shape) but with an ops audience/severity — do NOT call `notify_run_escalated`/`notify_run_failed` for ops events, and do NOT write ops alerts into a teacher's notification feed. A provider-breaker page must be invisible to teachers.
- [ ] **Reuse notification infra, add tiering** — build the ops sink on the existing `notification_store.py`/`notification_models.py` mechanics (or a sibling table) rather than a new stack; add a severity/tier field (page|warn) and an audience field (teacher|ops). Fail-closed: an alert that cannot be delivered must be persisted + retried, not dropped.
- [ ] **Evaluation cadence** — evaluate SLO/alert state on a schedule modeled on the existing recovery sweeper (`_run_teaching_pack_sweeper` loops every 60s at `services/gateway/main.py:70`; `recovery_sweeper.py`). Add an SLO/alert sweep alongside it rather than a new runtime. Deduplicate alerts (don't re-page every 60s for the same open condition — alert on state transition + periodic reminder).
- [ ] **Breaker-trip page wiring** — consume the `breaker_tripped` provider-scope events (OPS-01/OPS-03) and raise a PAGE. Run-scope breaker trips are healing noise → at most WARN/none.
- [ ] **Env mapping** — dev: alert *evaluation* may run but delivery is a log sink (no real paging); thresholds loose. staging/prod: real ops channel (paging integration), error budgets tracked, dedup active.

## Acceptance

- SLO objects exist for success ≥ 99.5% and p95 < 8 min (at minimum) reporting target, error budget, and burn, computed over OPS-03 KPI views.
- Forcing success below 99.5% (error-budget exhaustion) raises a **PAGE** to the ops channel and **no** teacher notification.
- A provider `breaker_tripped` event raises a PAGE; a run-scope breaker trip does not page.
- p95 crossing 8 min raises a **WARN**, not a page; queue-growing-but-draining is WARN; queue-not-draining is PAGE.
- Ops alerts are never visible in any teacher's notification feed (`notifications.py`); teacher escalations are never routed to the ops channel. Verified against the real notification store.
- Alerts dedup: a single sustained open condition pages once on transition (+ periodic reminder), not every sweep.
- Dev runs the evaluator with a log-only sink and does not require a paging integration.

## References

- `services/gateway/slo_metrics.py` — `compute_slo_snapshot` :45 (SLO source), `SloDimension` :14 (success_rate, run p95, queue_depth, gate_backlog, cost).
- OPS-03 KPI views (dependency) — escalate/day, healing distribution, breaker trips, tokens/run, per-stage p95.
- `services/gateway/notifications.py` — `notify_run_failed` :177, `notify_run_escalated` :199, `notify_gate_required` :53 (teacher channel — do NOT reuse for ops).
- `services/gateway/notification_store.py`, `notification_models.py`, `notification_db.py` (infra to mirror for the ops sink).
- `services/gateway/main.py:70` — `_run_teaching_pack_sweeper` (60s loop to model the SLO/alert sweep on); `recovery_sweeper.py` (`sweep_stuck_jobs` :33, `sweep_escalated_gates` :80).
- `packages/agents/healing/circuit_breaker.py:201` — `_emit_trip` (`breaker_tripped`, `scope` field for provider vs run).
- `packages/agents/events.py` — `escalate` :28, `healing_decision` :26, `breaker_tripped` :40.
- ADR-034 §2 (SLOs as monitored objects with error budgets; page vs warn; ops alerts separate from teacher escalate notices).

## Implementation notes

- Keep the SLO/alert *policy* a pure, table-testable evaluator: `evaluate_slos(kpi_snapshot) -> list[Alert(tier, audience, reason, key)]`. Delivery/dedup/persistence is the adapter around it. This mirrors how `check_backpressure`/`check_budget` are pure decisions with thin wiring.
- "Queue not draining" needs a *trend*, not a point value — compare pending/queued counts across consecutive sweeps (persist last N in a small table or the ops-alert store). Point-in-time queue depth alone can't distinguish a burst that will drain from a stuck queue.
- The DLQ signal depends on OPS-11 (dead-letter). Until OPS-11 lands, wire the DLQ-growth page against a placeholder count of 0 so the policy is complete and OPS-11 only has to populate the source. Note the coupling.
- Error-budget math: define the window (e.g. rolling 24h to match `slo_metrics` default `window=24h` at `slo_metrics.py:49`) and budget (0.5% of runs may fail). Burn rate drives whether success<99.5% is a slow-warn or fast-page.
- Dedup key should be the SLO/condition identity (e.g. `slo:run_success`, `breaker:provider:<name>`), so a flapping condition doesn't storm the pager.
- Do not create teacher-visible rows for ops alerts even accidentally — enforce the `audience` split at the store layer (separate table or a hard `audience='ops'` filter the teacher feed query already excludes).
