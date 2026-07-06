---
title: Make no-match and research-fail degradation explicit for hidden rollout
status: ready-for-agent
labels: [component-strategist, fallback, observability]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Define and implement the hidden/internal behavior for Component Strategist no-match, research-fail, and low-confidence cases. The system should fall back to the safe prose-only path, emit telemetry, and expose an internal/admin reason without silently choosing a default strategy.

This slice shares failure semantics with the existing fallback graph and feedback-conflict model, but narrows the behavior to internal production-hidden rollout.

## Acceptance criteria

- [ ] No-match and research-fail cases use a typed fallback state rather than silently selecting a default strategy.
- [ ] The safe prose-only path remains available when the strategist cannot produce a valid plan.
- [ ] Telemetry distinguishes no-match, research-fail, fallback-used, and hard blocked cases.
- [ ] Internal/admin or tester-visible output explains the fallback reason without leaking debug ledgers to normal teacher payloads.
- [ ] Tests cover no-match, research-fail, fallback-used, and safe path preservation.

## Blocked by

- CS-06 strategy quality gates and observability.
- CS-09 fallback graph and feedback conflicts.
- CS-15 minimum strategist telemetry.
