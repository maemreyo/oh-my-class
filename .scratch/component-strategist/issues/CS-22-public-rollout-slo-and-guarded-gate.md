---
title: Define full public rollout SLO and guarded rollout gate
status: ready-for-agent
labels: [component-strategist, observability, release-gate]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Promote internal rollout telemetry into the full public/default rollout gate. Before public enablement, the strategist should have measured baseline behavior, approved SLO thresholds, burn-rate or equivalent alerts, guarded rollout rollback behavior, and cleanup ownership for old/prose-only paths.

This slice is for public/default launch. It is intentionally stronger than the hidden/internal telemetry floor.

## Acceptance criteria

- [ ] Baseline measurement window captures strategist invocation, fallback/no-match, primary-tier-share, error, and latency behavior.
- [ ] Product-approved SLO thresholds are documented with rationale and error-budget policy.
- [ ] Rollout guard metrics can trigger rollback or keep the feature hidden when behavior regresses.
- [ ] Public rollout dashboard or equivalent view compares rollout variants and fallback/no-match trends.
- [ ] Cleanup owner and deadline exist for temporary flag/old-path behavior once public rollout succeeds.
- [ ] Tests or release-gate checks prove guard metrics are wired and rollback/off behavior still works.

## Blocked by

- CS-15 minimum strategist telemetry.
- CS-17 internal smoke benchmark.
