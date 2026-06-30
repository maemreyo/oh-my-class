# Topic Decomposition rollout checklist

> **Feature flag:** `features.topic_decomposition_v1`
> **ADR:** [ADR-017: Topic Decomposition and Unit Fan-Out](../adr/017-topic-decomposition-and-unit-fan-out.md)
> **Tracking issues:** 001-019 (`.scratch/topic-decomposition/`)
> **Phase 1 scope:** Sequential fan-out (`unit_fanout_concurrency = 1`), happy-path + failure recovery. Phase 2/3 features (parallel intra-layer, soft-block override polish, decomposition memory, knowledge graph, coherence lint, personalization) ship behind the same flag incrementally.

---

## 1. Dev validation

- [ ] Enable `features.topic_decomposition_v1` in local dev config; confirm it gates the full surface: triage stage, `plan_unit` path, unit gate, fan-out, unit workspace, orchestrator reactor, reconciliation sweep branch, unit event emission, unit endpoints, and eval harness. **(issue 019)**
- [ ] Disable the flag and run the standard single-lesson E2E to confirm baseline is unchanged: no triage suggestion, no `/units` route, `plan_unit` rejected predictably, orchestrator reactor + sweep branch + unit event emission inactive. **(issue 019)**
- [ ] Run `make test` and `make check`; all suites pass, including prior issues' tests. **(issue 019)**
- [ ] Run `uv run pytest tests/e2e/test_unit_flow.py tests/e2e/test_unit_failure_recovery.py -v` against real DB + real LLM (9router port 20228, model `4omc`). **(issue 019)**
- [ ] Verify exported unit HTML bundle contains all sessions, sequence overview, and locked theme; confirm standalone (no CDN, no external assets). **(issues 017, 019)**
- [ ] Confirm `unit_fanout_concurrency = 1` in dev config; children spawn sequentially in topological order. **(issue 019, ADR-017)**
- [ ] Run the golden-topics eval harness (`uv run pytest tests/eval/test_decomposition_quality.py -v`) with at least 3 topics spanning subjects and locales. Confirm all invariants hold: acyclic DAG, 2+ Bloom levels, 4 or fewer new KCs/session, duration drift within 10%, every session has a methodology, all prerequisite references resolve, `grounding_status` is `grounded` or `partial` for known topics. **(issue 018)**
- [ ] Confirm the eval harness catches a deliberate invariant violation (drift sentinel test). **(issue 018)**

---

## 2. Staging validation

- [ ] Deploy the flag to staging only; confirm it does not affect production config. **(issue 019)**
- [ ] Run the full E2E happy-path scenario on staging: teacher submits a multi-tiết topic, triage suggests a unit, teacher confirms, reviews/edits the sequence at `UNIT_APPROVAL`, approves, children fan out (sequential, topo order), teacher reviews sessions in the dashboard, approves all, exports a unit bundle. **(issue 019)**
- [ ] Run the failure-path E2E on staging: force a child session failure, confirm the unit stays alive, teacher retries that session, unit completes. **(issue 019)**
- [ ] Confirm unit-scoped events appear in the observability dashboard: `unit.created`, fan-out size, per-session status transitions, `grounding_status`, confidence, validator issues, coherence warnings, teacher edits at the unit gate, blocked/override counts, partial-vs-complete, per-unit token/cost rollup. **(issue 018)**
- [ ] Confirm the `SequenceConsistencyValidator` fires on staging with correct hard/advisory distinctions: acyclic DAG (hard), KC count (hard), Bloom (hard), duration drift (hard), session count advisory only. **(ADR-017)**
- [ ] Confirm the no-silent-downgrade invariant holds on staging: a unit-plan failure surfaces an error/escalation, never a single-lesson substitute. **(issue 019)**
- [ ] Validate quality-gate warnings and critical failures appear in run metadata. **(issue 019)**
- [ ] Confirm parent token/cost equals the sum of its children's token/cost. **(issue 018)**

---

## 3. Beta teacher enablement

- [ ] Select beta teachers using these criteria:
  - Teach multi-tiết topics regularly (2+ tiết/chủ đề per week).
  - Comfortable with sequence editing and batch approval in the dashboard.
  - Willing to provide feedback on decomposition quality and gate UX.
  - No reliance on legacy `/run/approvals` route (frozen under ADR-017).
- [ ] Enable the flag for the beta cohort only, via teacher allow-list or feature-flag per-teacher toggle. **(issue 019)**
- [ ] Confirm the unit workspace UI is accessible for beta teachers (sequence editor, unit dashboard, batch "Approve all" for child content gates). **(issue 012, issue 019)**
- [ ] Provide beta teachers with a brief guide: how to trigger decomposition (multi-tiết topic input), how to review/edit the sequence at `UNIT_APPROVAL`, how to batch-approve child sessions, how to retry a failed session.
- [ ] Set up a dedicated feedback channel (Slack thread or issue tracker label `topic-decomposition-beta`) for beta teacher input.
- [ ] Track per-teacher metrics: approval rate, edit rate, reject-and-replan rate, retry rate. **(issue 018)**

---

## 4. Fallback and escalation behavior

- [ ] **No silent downgrade.** When a unit plan or fan-out fails, the system fails closed or escalates to the teacher. It never silently falls back to a single lesson. Verify with the dedicated test: `tests/e2e` suite includes a no-silent-downgrade test. **(issue 019)**
- [ ] When `features.topic_decomposition_v1` is disabled, all unit surfaces are inactive and the system behaves exactly as baseline (single-lesson flow). **(issue 019)**
- [ ] Child session failure keeps the unit alive; the failed child is retried by resuming its existing child run, not by creating a new row (guarded by DB unique constraint `(parent_run_id, session_id)` + app-level key `fanout:{unit_id}:{seq_revision}`). **(ADR-017)**
- [ ] Unit reaches `partially_complete` and is exportable before all sessions finish. **(ADR-017)**
- [ ] Prerequisite soft-block: a session blocked by an incomplete prerequisite is not spawned; teacher override unblocks it. **(ADR-017)**
- [ ] Repair exhaustion path: after the maximum repair attempts (3 cycles), escalate to the teacher via the gate with the failing-case feedback preserved. **(ADR-017, issue 009)**
- [ ] Orchestrator is stateless and crash-safe: on restart, it recomputes unit state from durable storage (`TeachingPackJobStore` + run rows), not from in-memory event bus. The reconciliation sweep is the correctness backstop. **(ADR-017)**
- [ ] When the flag is off or disabled, standard generation (single-lesson) is unaffected. Confirm via regression: `make test` passes with the flag toggled off. **(issue 019)**

---

## 5. Metrics to monitor

All metrics are unit-scoped, tagged with `unit_id`, `run_id`, `session_id`, and teacher ID. They flow through the existing observability substrate (Langfuse tags + run events). **(issue 018)**

### 5.1 Decomposition metrics

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| `unit.created` event count | Unit orchestrator | 0 for 24h after beta enablement |
| Fan-out size per unit | Unit orchestrator | 0 or >8 sessions per unit |
| `grounding_status` distribution | Unit planner | >20% `ungrounded` in a day |
| `confidence` score distribution | Unit planner | Median <0.7 for a subject |
| Sequence consistency violations | `SequenceConsistencyValidator` | Any hard violation |
| Coherence lint warnings | `coherence_judge` | >5 warnings per unit |
| Teacher edits at unit gate | `UNIT_APPROVAL` gate | >50% units edited (too many?) or 0% (not reviewing?) |
| Blocked/override counts | Orchestrator | >3 overrides per unit |

### 5.2 Pipeline metrics

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| Per-unit token/cost rollup | Child aggregation | Cost >2x single-lesson baseline |
| Per-session status transitions | Run events | Session stuck in `generating` >30min |
| Child session failure rate | Run status | >10% failure rate in a day |
| Retry success rate | Run resume | <50% success after retry |
| Partial completion rate | `partially_complete` units | >20% of units never reach `complete` |
| Export pass/fail | Export pipeline | Any export failure for a unit bundle |

### 5.3 Dashboard and alerting

- [ ] Dashboard link documented in team runbook (specific URL depends on your Langfuse/Grafana deployment).
- [ ] Alert rules configured for all thresholds above.
- [ ] Nightly eval harness result published to the same dashboard (`tests/eval/test_decomposition_quality.py` pass/fail + invariant breakdown). **(issue 018)**
- [ ] Per-unit token/cost equals sum of children: verify via a daily assertion test or dashboard panel. **(issue 018)**

---

## 6. Kill switch procedure

The kill switch is the feature flag itself: `features.topic_decomposition_v1`.

### 6.1 Immediate kill (flag off)

- [ ] Set `features.topic_decomposition_v1 = false` in the config source (environment variable, YAML, or feature-flag service).
- [ ] Restart or hot-reload the gateway service (`services/gateway`).
- [ ] Confirm: no new units are created, no triage suggestions fire, `/units` route is inactive, orchestrator reactor + sweep branch + unit event emission are dormant. **(issue 019)**
- [ ] Existing in-flight units: children already running will complete their individual runs (they are independent LangGraph threads). No new children are spawned for those units.
- [ ] Notify beta teachers that decomposition is temporarily disabled; they should submit single-tiết topics or wait.

### 6.2 Partial rollback (concurrency reduction)

- [ ] If the issue is excessive parallelism or resource contention, reduce `unit_fanout_concurrency` to 1 (Phase 1 default) without disabling the flag. No code change needed, config only. **(ADR-017)**
- [ ] Confirm children return to sequential topological order.

### 6.3 Escalation path

- [ ] If the flag-off still leaves stale unit data in the UI, clear the unit cache or restart the frontend (`apps/web`).
- [ ] If a specific unit is stuck, resume it via `POST /teaching-packs/runs/{id}/resume` with an escalation response to force the gate.
- [ ] File an incident with the unit_id, run_ids, and the failing stage for postmortem.

### 6.4 Rollback verification

- [ ] After any kill-switch action, run `make test` with the flag off to confirm baseline is intact. **(issue 019)**
- [ ] Confirm the standard single-lesson E2E still passes.
- [ ] Confirm no broken UI/endpoints when the flag is off. **(issue 019)**

---

## 7. Phase 1 to Phase 2 progression

Phase 1 ships with `unit_fanout_concurrency = 1` (sequential topological fan-out). Phase 2 raises the concurrency cap. Same code, config only. **(ADR-017, issue 019)**

### 7.1 Phase 1 promotion criteria

- [ ] All dev/staging validation steps complete. **(sections 1-2)**
- [ ] Beta teacher cohort has run at least 20 units with no critical failures.
- [ ] Child session failure rate stays below 10% over a 7-day window.
- [ ] No silent downgrade incidents logged.
- [ ] `SequenceConsistencyValidator` hard violations are zero (or explained and acknowledged).
- [ ] Nightly eval harness passes all golden topics for 7 consecutive nights.
- [ ] Beta teacher feedback is net positive (approval rate >80%, no UX-blocking complaints).
- [ ] Token/cost per unit is within 2x the single-lesson baseline for 80%+ of units.
- [ ] Observability dashboard is live and alerts are firing for configured thresholds.
- [ ] Rollback procedure has been tested (flag off, verify baseline).

### 7.2 Phase 2 readiness checklist

- [ ] Raise `unit_fanout_concurrency` to 2-3 in staging. Confirm no deadlocks, race conditions, or DB constraint violations. **(ADR-017)**
- [ ] Confirm the stateless orchestrator handles concurrent child settlements correctly (recompute from durable storage on each trigger). **(ADR-017)**
- [ ] Monitor resource usage (DB connections, LLM concurrency limits on 9router) under parallel fan-out.
- [ ] Run the eval harness with parallel fan-out; invariants must still hold.
- [ ] Stress test: 5 concurrent units, 4+ sessions each, all running in parallel.
- [ ] Confirm the batch "Approve all" UI handles multiple pending gates arriving simultaneously.
- [ ] Update `unit_fanout_concurrency` in production config. No code deploy needed.
- [ ] Monitor for 14 days before considering further concurrency increases.

---

## Appendix: issue cross-reference

| Section | Issues covered |
|---------|---------------|
| Feature flag gating | 019 |
| E2E happy path | 019 |
| E2E failure recovery | 019 |
| No silent downgrade | 019, ADR-017 |
| Observability events/metrics | 018 |
| Eval harness | 018 |
| Unit workspace / dashboard | 012, 019 |
| Coherence lint | 016 |
| Unit packager / export | 017 |
| Orchestrator / fan-out | 010, ADR-017 |
| Unit planner agent | 006 |
| Stage wiring / unit gate | 007 |
| Context propagation | 009 |
