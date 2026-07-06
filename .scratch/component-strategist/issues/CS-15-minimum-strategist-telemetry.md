---
title: Add minimum strategist telemetry for internal rollout
status: ready-for-agent
labels: [component-strategist, observability, rollout]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Add the minimum telemetry needed to safely run Component Strategist in hidden/internal production. Operators should be able to see whether the strategist ran, what strategy/component it selected, whether it fell back or no-matched, and how long it took, without exposing raw teacher text or student data.

This is the internal rollout telemetry floor, not the full public SLO/burn-rate system.

## Acceptance criteria

- [ ] Strategy invocations emit structured counts tagged by request/run/teacher/environment and feature variant.
- [ ] Selected strategy family and component types are observable without leaking raw prompt, raw lesson text, student PII, or debug ledgers.
- [ ] Fallback rate, no-match rate, error count, and latency are emitted for strategist runs.
- [ ] Telemetry remains useful when the strategist falls back to prose-only behavior.
- [ ] Tests prove events include required tags and exclude raw teacher/student-sensitive content.

## Blocked by

- CS-06 strategy quality gates and observability.
- CS-11 cache, privacy, and observability-retention boundaries.
