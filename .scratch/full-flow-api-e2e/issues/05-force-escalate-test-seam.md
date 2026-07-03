# [FFA-05] `TEACHING_PACK_FORCE_ESCALATE` test seam + guard

Status: TODO
Labels: full-flow-api, healing, testing
ADR: 029
Depends on: FFA-04

## Context

Escalation depends on repeated real quality failures, which cannot be produced
deterministically over HTTP. The FFA-10 driver and CI need a deterministic way to exercise
the escalate scenario without relying on LLM output quality.

## Scope

- [ ] Add a test-only env flag `TEACHING_PACK_FORCE_ESCALATE` read in `heal_quality_failure`
      (`teaching_pack/healing_runtime.py`) that short-circuits to the escalate outcome
      (`escalate=true`, route `teacher_approval`).
- [ ] Off by default; must NOT change production behaviour when unset.
- [ ] Guard test asserting the seam is inert unless explicitly set to a truthy value.
- [ ] Document the flag as test/demo-only (not for production config).

## Acceptance

- With the flag set, a run reaches the escalated `content_approval` gate on first quality
  evaluation; with it unset, healing behaves normally (ladder from FFA-03).
- Guard test proves no escalation when the flag is absent/empty.

## References

- ADR-029. `teaching_pack/healing_runtime.py`. Consumed by FFA-10 (driver escalate scenario).
