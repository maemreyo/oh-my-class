# Topic Decomposition rollout checklist

> **Feature flag:** `FEATURE_TOPIC_DECOMPOSITION_V1`
> **ADR:** [ADR-017: Topic Decomposition and Unit Fan-Out](../adr/017-topic-decomposition-and-unit-fan-out.md)
> **Tracking issues:** 001–019 (`.scratch/topic-decomposition/`)
> **Phase 1 scope:** Sequential fan-out (`UNIT_FANOUT_CONCURRENCY=1`), happy-path + failure recovery.
> Phase 2/3 features (parallel intra-layer, soft-block override polish, decomposition memory, knowledge graph, coherence lint, personalization) ship behind the same flag incrementally.

---

## 1. Feature flag: FEATURE_TOPIC_DECOMPOSITION_V1=true

The entire topic-decomposition surface is gated by a single environment variable. No code changes are required to enable or disable it.

**To enable:**

```bash
# In your .env file or deployment config:
FEATURE_TOPIC_DECOMPOSITION_V1=true
UNIT_FANOUT_CONCURRENCY=1   # Phase 1: sequential (safe default)
```

**What the flag gates:**

- Triage stage: `plan_unit` suggestion fires only when flag is on.
- `plan_unit` routing path in `packages/agents/teaching_pack/nodes.py`.
- `UNIT_APPROVAL` gate and unit workspace routes.
- `UnitOrchestrator` fan-out reactor (`services/gateway/unit_orchestrator.py`).
- Reconciliation sweep branch in `services/gateway/main.py`.
- Unit event emission (`unit.created`, `unit.completed`, etc.).
- `/units/...` API endpoints (`services/gateway/routers/unit_runs.py`).
- Unit evaluation harness (`tests/eval/test_decomposition_quality.py`).

**To read the flag in code:**

```python
from packages.agents.config.features import features

if features().topic_decomposition_v1:
    # unit path
```

**UNIT_FANOUT_CONCURRENCY** controls parallel fan-out (Phase 2). Default `1` means children are spawned sequentially in topological order. Raise to `2`–`3` for Phase 2 only after Phase 1 promotion criteria are met (see §8).

---

## 2. Dev validation

- [ ] Enable `FEATURE_TOPIC_DECOMPOSITION_V1=true` in local dev config; confirm it gates the full surface: triage stage, `plan_unit` path, unit gate, fan-out, unit workspace, orchestrator reactor, reconciliation sweep branch, unit event emission, unit endpoints, and eval harness. **(issue 019)**
- [ ] Run `make test` and `make check`; all suites pass, including tests from prior issues. **(issue 019)**
- [ ] Run the E2E suite against real DB + real LLM (9router port 20228, model `4omc`):

  ```bash
  uv run pytest tests/e2e/test_unit_flow.py tests/e2e/test_unit_failure_recovery.py -v
  ```

- [ ] Confirm `UNIT_FANOUT_CONCURRENCY=1` in dev config; children spawn sequentially in topological order.
- [ ] Disable the flag and run the standard single-lesson E2E to confirm baseline is unchanged: no triage suggestion, no `/units` route, `plan_unit` rejected predictably, orchestrator reactor + sweep branch + unit event emission inactive. **(issue 019)**
- [ ] Verify exported unit HTML bundle contains all sessions, sequence overview, and locked theme; confirm standalone (no CDN, no external assets). **(issues 017, 019)**
- [ ] Run the golden-topics eval harness with at least 3 topics spanning subjects and locales:

  ```bash
  uv run pytest tests/eval/test_decomposition_quality.py -v
  ```

  Confirm all invariants hold: acyclic DAG, 2+ Bloom levels, ≤4 new KCs/session, duration drift within 10%, every session has a methodology, all prerequisite references resolve, `grounding_status` is `grounded` or `partial` for known topics. **(issue 018)**

- [ ] Confirm the eval harness catches a deliberate invariant violation (drift sentinel test). **(issue 018)**

---

## 3. Staging validation

- [ ] Deploy `FEATURE_TOPIC_DECOMPOSITION_V1=true` to staging only; confirm it does not affect production config.
- [ ] Run the full E2E happy-path scenario on staging:
  1. Teacher submits a multi-tiết topic.
  2. Triage suggests a unit plan.
  3. Teacher confirms.
  4. Sequence appears at `UNIT_APPROVAL`; teacher reviews, edits if needed, and approves.
  5. Children fan out (sequential, topological order).
  6. Teacher reviews sessions in the unit dashboard and approves all.
  7. Teacher exports a unit bundle.
- [ ] Run the failure-path E2E on staging: force a child session failure, confirm the unit stays alive as `PARTIALLY_COMPLETE`, teacher retries that session, unit completes. **(issue 019)**
- [ ] Confirm Langfuse traces contain all unit-scoped events:
  - `unit.created` with `fan_out_size`, `grounding_status`, and `confidence`.
  - Per-session `status` transitions.
  - Validator issues and coherence warnings.
  - Teacher edits at the unit gate.
  - Blocked/override counts.
  - `partial_complete` vs `complete` final states.
  - Per-unit token/cost rollup equals the sum of its children.
- [ ] Confirm the `SequenceConsistencyValidator` fires on staging with correct hard/advisory distinctions: acyclic DAG (hard), KC count (hard), Bloom (hard), duration drift (hard), session count advisory only. **(ADR-017)**
- [ ] Confirm the no-silent-downgrade invariant holds on staging: a unit-plan failure surfaces as an error/escalation event, never as a single-lesson substitute. **(issue 019)**
- [ ] Validate quality-gate warnings and critical failures appear in run metadata.

---

## 4. Beta teacher enablement

**Selection criteria:**

- Teaches multi-tiết topics regularly (2+ tiết/chủ đề per week).
- Comfortable with sequence editing and batch approval in the dashboard.
- Willing to provide feedback on decomposition quality and gate UX.
- Does not rely on the legacy `/run/approvals` route (frozen under ADR-017).

**Enablement steps:**

- [ ] Enable the flag for the beta cohort only, via teacher allow-list or per-teacher feature-flag toggle.
- [ ] Confirm the unit workspace UI is accessible for beta teachers: sequence editor, unit dashboard, batch "Approve all" for child content gates. **(issue 012, issue 019)**
- [ ] Provide beta teachers with an onboarding guide:
  - How to trigger decomposition (submit a multi-tiết topic input).
  - How to review and edit the sequence at `UNIT_APPROVAL`.
  - How to batch-approve child sessions in the dashboard.
  - How to retry a failed session.
- [ ] Set up a dedicated feedback channel (Slack thread or issue label `topic-decomposition-beta`) for beta teacher input.
- [ ] Track per-teacher metrics: approval rate, edit rate, reject-and-replan rate, retry rate. **(issue 018)**

---

## 5. Fallback / kill switch

The kill switch is the feature flag itself.

### 5.1 Immediate disable (flag off)

```bash
FEATURE_TOPIC_DECOMPOSITION_V1=false
```

Restart or hot-reload `services/gateway`. Effect is immediate:

- No new units are created.
- No triage suggestions fire.
- `/units/...` routes return 404/503.
- Orchestrator reactor, sweep branch, and unit event emission are dormant.

**In-flight units:** children already running will complete their individual runs (they are independent LangGraph threads). No new children are spawned for those units.

- [ ] Notify beta teachers that decomposition is temporarily disabled; they should submit single-tiết topics or wait.

### 5.2 Partial rollback (concurrency reduction only)

If the issue is excessive parallelism or resource contention, reduce `UNIT_FANOUT_CONCURRENCY` to `1` without disabling the flag. No code change needed — config only. **(ADR-017)**

### 5.3 Escalation path

- If the flag-off still leaves stale unit data in the UI, clear the unit cache or restart `apps/web`.
- If a specific unit is stuck, resume it via `POST /teaching-packs/runs/{id}/resume` with an escalation response to force the gate.
- File an incident with the `unit_id`, `run_id`s, and the failing stage for postmortem.

### 5.4 Rollback verification

- [ ] After any kill-switch action, run `make test` with the flag off to confirm baseline is intact.
- [ ] Confirm the standard single-lesson E2E still passes.
- [ ] Confirm no broken UI or endpoints when the flag is off.

**No data loss on disable:** unit rows, child run rows, and lesson sequences remain in the DB. Re-enabling the flag allows in-flight units to resume from durable state. The orchestrator is stateless and crash-safe — it recomputes unit state from `TeachingPackJobStore` + run rows on each sweep tick, never from in-memory event bus. **(ADR-017)**

---

## 6. Metrics to monitor (Langfuse / observability)

All metrics are tagged with `unit_id`, `run_id`, `session_id`, and teacher ID.

### 6.1 Core unit events

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| `unit.created` event count | Unit orchestrator | 0 events for 24 h after beta enablement |
| `unit.completed` rate | Unit orchestrator | <50% of created units complete in 48 h |
| `failed_sessions` rate | Run events | >10% session failure rate in a rolling day |
| Average `fan_out_size` | Unit orchestrator | 0 or >8 sessions per unit |
| `grounding_status` distribution | Unit planner | >20% `ungrounded` in a day |
| `confidence` score | Unit planner | Median <0.7 for any subject |

### 6.2 Cost vs baseline

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| Per-session token/cost vs single-lesson baseline | Child aggregation | Any session >2× baseline |
| Per-unit rollup = sum of children | Cost audit | Any mismatch |

### 6.3 Pipeline health

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| Session stuck in `generating` | Run events | >30 min in generating state |
| Retry success rate | Run resume | <50% success on retry |
| Partial completion rate | `partially_complete` units | >20% of units never reach `complete` |
| Export pass/fail | Export pipeline | Any export failure for a unit bundle |
| Sequence consistency violations | `SequenceConsistencyValidator` | Any hard violation |
| Coherence lint warnings | `coherence_judge` | >5 warnings per unit |

### 6.4 Dashboard and alerting checklist

- [ ] Dashboard link documented in team runbook.
- [ ] Alert rules configured for all thresholds above.
- [ ] Nightly eval harness result published to dashboard (`tests/eval/test_decomposition_quality.py` pass/fail + invariant breakdown). **(issue 018)**
- [ ] Per-unit token/cost equals sum of children: daily assertion test or dashboard panel. **(issue 018)**

---

## 7. No-silent-downgrade guarantee

**Invariant:** when a unit plan or fan-out fails, the system fails closed or escalates to the teacher. It never silently substitutes a single-lesson output.

**Enforcement points:**

1. `unit_planner_node` raises `ClarificationRequiredError` (or `ValueError`) for ambiguous/empty requests — never returns a 1-session sequence.
2. A failed unit plan emits an `error` run event visible in Langfuse — not a silent fallback path.
3. The `test_no_silent_downgrade` test in `tests/e2e/test_unit_flow.py` asserts this at the unit-planner boundary.
4. The `TestNoSilentDowngrade` class in the existing E2E suite covers the contract at the teaching-pack level.

**Verification:**

- [ ] Run `uv run pytest tests/e2e/test_unit_flow.py::test_no_silent_downgrade -v` — must pass.
- [ ] On staging, trigger a deliberate ambiguous request; confirm an `error` event appears in Langfuse, no lesson HTML is emitted.

---

## 8. Phase 2 gate: raise UNIT_FANOUT_CONCURRENCY > 1

Phase 1 ships with `UNIT_FANOUT_CONCURRENCY=1` (serial topological fan-out). Phase 2 raises the cap. Same code, config change only. **(ADR-017)**

### 8.1 Phase 1 promotion criteria (all must be met)

- [ ] All dev and staging validation steps in §2–§3 are complete.
- [ ] Beta teacher cohort has run ≥20 units with no critical failures.
- [ ] Child session failure rate stays below 10% over a 7-day window.
- [ ] No silent-downgrade incidents logged.
- [ ] `SequenceConsistencyValidator` hard violations are zero (or explicitly acknowledged).
- [ ] Nightly eval harness passes all golden topics for 7 consecutive nights.
- [ ] Beta teacher approval rate >80%; no UX-blocking complaints.
- [ ] Per-unit token/cost is within 2× single-lesson baseline for ≥80% of units.
- [ ] Observability dashboard is live; all alerts from §6 are active.
- [ ] Rollback procedure has been exercised: flag toggled off, baseline confirmed intact.

### 8.2 Phase 2 readiness checklist

- [ ] Raise `UNIT_FANOUT_CONCURRENCY` to 2–3 on staging. Confirm no deadlocks, race conditions, or DB unique-constraint violations.
- [ ] Confirm the stateless orchestrator handles concurrent child settlements correctly: it recomputes from durable storage on each trigger tick, never from in-memory state. **(ADR-017)**
- [ ] Monitor resource usage (DB connection pool, 9router LLM concurrency limits) under parallel fan-out.
- [ ] Run the eval harness with parallel fan-out; all invariants must still hold.
- [ ] Stress test: 5 concurrent units, ≥4 sessions each, all running in parallel.
- [ ] Confirm the batch "Approve all" UI handles multiple pending gates arriving simultaneously.
- [ ] Update `UNIT_FANOUT_CONCURRENCY` in production config. No code deploy required.
- [ ] Monitor for 14 days before any further concurrency increase.

---

## Appendix: issue cross-reference

| Section | Issues covered |
|---------|----------------|
| Feature flag gating | 019 |
| E2E happy path | 019 |
| E2E failure recovery | 019 |
| No silent downgrade | 019, ADR-017 |
| Observability events / metrics | 018 |
| Eval harness | 018 |
| Unit workspace / dashboard | 012, 019 |
| Coherence lint | 016 |
| Unit packager / export | 017 |
| Orchestrator / fan-out | 010, ADR-017 |
| Unit planner agent | 006 |
| Stage wiring / unit gate | 007 |
| Context propagation | 009 |
