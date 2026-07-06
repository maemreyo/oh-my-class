---
title: Keep LLM advisor deferred behind explicit future gate
status: ready-for-agent
labels: [component-strategist, llm, security]
created: 2026-07-06
---

## Parent

`.omo/ulw-research/20260706-103328-component-strategist-web/ROUGH-REPORT-verdicts-and-direction.md`

## What to build

Make the LLM advisor path explicitly unavailable for v1 deterministic rollout unless a future gate is satisfied. The future gate should require evaluation proof, off switch, decision-source telemetry, prompt/data isolation, cost attribution, and privacy/security review before any LLM tie-break or rationale advisor can affect strategy decisions.

This slice preserves the v1 deterministic posture and prevents accidental half-enabled LLM behavior.

## Acceptance criteria

- [ ] v1 strategist behavior remains deterministic-only by default.
- [ ] Any LLM advisor path is behind an explicit disabled-by-default control separate from the main strategist rollout control.
- [ ] Attempts to enable the advisor without an eval harness and security/privacy prerequisites fail closed or are rejected by configuration validation.
- [ ] Future advisor output, when eventually enabled, must carry `decision_source` telemetry and be safely ignored on timeout, parse failure, or schema mismatch.
- [ ] Tests prove the advisor is unavailable in v1 default/internal rollout and cannot silently influence selector decisions.

## Blocked by

- CS-15 minimum strategist telemetry.
- CS-22 public rollout SLO and guarded rollout gate.
