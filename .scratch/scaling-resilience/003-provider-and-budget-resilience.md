---
title: Provider-exhaustion resilience and budget degradation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Stop turning transient LLM-provider exhaustion into hard run failures. Today an all-providers-down / free-tier-exhausted error propagates from the LLM transport → worker `except` → job `FAILED`. The job store already has `eligible_at` + QUEUED→PENDING promotion (a delayed-retry mechanism) that is not wired to exhaustion.

- **Typed failure classification**: the transport raises a typed error distinguishing **transient** (free-tier exhausted / 429 / all-providers-down / timeout) from **permanent** (bad prompt, schema, budget ceiling). Transient → **requeue with `eligible_at = now + backoff`** (reuse the existing mechanism); permanent → `FAILED`.
- **Teacher-facing status**: a requeued-for-quota run shows a "waiting for quota / queued" state + event (`delayed_provider_quota`), not `FAILED`. The sweeper/promotion re-runs it when `eligible_at` arrives.
- **Budget vs exhaustion (distinct)**: per-run `BudgetExceededError` = **hard-stop** (prevents runaway cost) but with a clear teacher message and **preserved `completed_stages`** (no discard); optionally **degrade to a cheaper/compressed model** (e.g. `deepseek-compressed`) as a final tier before hard-stop if policy allows.
- **Per-provider circuit breaker**: app-level backoff that respects 9Router's `free_tier_exhausted`/`provider_down` signals — stop hammering a dead provider.

## Acceptance criteria

- [ ] Transport errors are typed transient vs permanent; transient → requeue with backoff via `eligible_at`, permanent → `FAILED`.
- [ ] A quota-requeued run surfaces a "waiting/queued" status + `delayed_provider_quota` event, not `FAILED`, and auto-resumes when eligible.
- [ ] `BudgetExceededError` hard-stops with a clear message and preserved `completed_stages`; optional degrade-to-cheap tier is config-gated.
- [ ] A per-provider circuit breaker backs off on `free_tier_exhausted`/`provider_down` and recovers.
- [ ] No silent quality downgrade: degradation (if enabled) is explicit and recorded; otherwise hard-stop.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`; provider-exhaustion simulated at the transport boundary.)

- [ ] `services/gateway/tests/test_provider_exhaustion_requeue.py`: a simulated free-tier-exhausted error requeues the job with `eligible_at` and emits `delayed_provider_quota` (status not FAILED); promotion re-runs it.
- [ ] `services/gateway/tests/test_permanent_failure_fails.py`: a bad-prompt/schema error → `FAILED` (not requeued).
- [ ] `packages/agents/tests/test_budget_hardstop.py`: `BudgetExceededError` hard-stops, preserves `completed_stages`, and (flag on) degrades to compressed model before stopping.
- [ ] `services/gateway/tests/test_provider_circuit_breaker.py`: repeated provider-down signals trip the breaker (backoff) and recover after cooldown.
- [ ] Run `uv run pytest services/gateway/tests/test_provider_*.py packages/agents/tests/test_budget_hardstop.py services/gateway/tests/test_permanent_failure_fails.py -v`.

## Blocked by

- .scratch/scaling-resilience/001-worker-pool-and-lease-heartbeat.md
