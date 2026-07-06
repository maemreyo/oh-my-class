---
title: Add internal smoke benchmark for strategist index and selector
status: ready-for-agent
labels: [component-strategist, qa, performance]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Add an internal smoke benchmark that proves the static strategy index and deterministic selector are safe enough for hidden/internal production enablement. The benchmark should exercise representative fixture requests and verify read-only opening, query shape, selector output shape, latency, and fallback/no-match sanity.

This is not the full public rollout load test; it is the minimum evidence for pre-user production-hidden rollout.

## Acceptance criteria

- [ ] Benchmark opens the generated SQLite index read-only and runs representative index queries.
- [ ] Benchmark runs representative selector fixtures and verifies result shape, selected moves/components, and fallback/no-match counts.
- [ ] Benchmark records internal p95 latency against a documented temporary threshold.
- [ ] Benchmark fails when representative queries return malformed results or abnormal fallback/no-match behavior.
- [ ] The smoke benchmark is runnable from a documented CLI or test command and can be used by release gate automation.

## Blocked by

- CS-03 selector, scorer, and diversity core.
- CS-08 golden scenarios, CLI smoke, and E2E release gate.
- CS-16 static read-only index policy.
