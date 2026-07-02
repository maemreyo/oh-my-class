# Issue #18: [Epic][Phase 5] Teacher trust UX

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/18
State: OPEN
Created: 2026-07-02T16:42:13Z
Updated: 2026-07-02T16:42:13Z
Labels: enhancement, agents-refactor, phase-5
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

Teachers currently approve or reject at the gate with almost no explanation of why the system judged an artifact the way it did. This epic adds the trust layer: an explainable teacher gate, live status, and escalation notifications. It is **additive UI** built on top of everything else — it consumes the observability backbone (Phase 2), the judge rationale and compliance results (Phase 3), and the resilience/escalation signals (Phase 4). It builds nothing new in the pipeline core.

This is a production-ready rebuild of the teacher-facing surface, NOT patching. It reuses existing checkpoint/interrupt machinery and the single observability event stream — it must not spawn a second telemetry pipeline. High-readability, SoC, modular, testable.

## Scope

Child issue (separate in this milestone):

- [ ] Explainable teacher gate + live status + escalate notification.

Coordination:

- [ ] All teacher-visible signals must derive from the single `ObservabilityEvent` stream (Phase 2), not a new source.
- [ ] Fast-lane UI affordances must match ADR-026 (auto-approve label, view-details, revert window).
- [ ] Scoped approve/reject actions must match the scoped-replan model from Phase 3.

## Acceptance

- [ ] Explainable-gate child issue closed with tests.
- [ ] Teacher can see judge rationale, revision count, healing history, and approval mode per `artifact_id`.
- [ ] Live status bar renders from `ObservabilityEvent` with no second pipeline.

## References

- ADR: `docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`
- Verdict: `docs/reports/agents/07-ux-teacher-trust-flow.md`

## Depends on

- Phase 2 (state + observability), Phase 3 (judge rationale + compliance + scoped replan), Phase 4 (escalation signals). See milestone `agents-hardening`.

