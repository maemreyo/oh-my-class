---
title: Per-teacher cost cap and transparency
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Prevent a single teacher exhausting free-tier / runaway cost, and show usage. Per-run `BudgetLedger` + backpressure exist; extend to a per-teacher rolling window with graceful degradation (not hard-fail).

- **Per-teacher rolling cost cap** (per-day/month): extend `BudgetLedger`; on breach → **defer/requeue** via `eligible_at` (scaling-resilience 003) or notify, **never hard-fail** mid-work.
- **Transparency**: surface the teacher's own usage on the dashboard — framed simply ("còn X bài tháng này" for free-tier; tokens/cost for paid), per class where useful.
- Ties to SLO cost/day alerting (issue 001).

## Acceptance criteria

- [ ] A per-teacher rolling cost cap is enforced; breach defers/requeues or notifies, never hard-fails an in-flight run.
- [ ] The teacher dashboard shows their own usage/quota in plain framing.
- [ ] Caps are configurable; global cost/day alerting (issue 001) is consistent with per-teacher caps.

## Detailed test suite

(Real DB.)

- [ ] `services/gateway/tests/test_per_teacher_cost_cap.py`: exceeding the rolling cap defers a new run (eligible_at set) or notifies; an in-flight run is not hard-failed.
- [ ] `apps/web/tests/usage-quota.test.tsx`: the dashboard renders the teacher's usage/quota correctly.
- [ ] Run `uv run pytest services/gateway/tests/test_per_teacher_cost_cap.py -v` and `pnpm -F web test`.

## Blocked by

- .scratch/scaling-resilience/003-provider-and-budget-resilience.md
