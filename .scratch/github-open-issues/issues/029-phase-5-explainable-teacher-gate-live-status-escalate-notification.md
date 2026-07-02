# Issue #29: [Phase 5] Explainable teacher gate + live status + escalate notification

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/29
State: OPEN
Created: 2026-07-02T16:43:01Z
Updated: 2026-07-02T16:43:01Z
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

Teachers approve/reject at the gate with little explanation and no live visibility, and escalations are invisible. This issue builds the explainable teacher gate, a live status bar, and escalation notifications. It is additive UI on top of the foundation: it consumes the judge rationale (Phase 3), compliance results (Phase 3), the single `ObservabilityEvent` stream (Phase 2), and escalation signals (Phase 4). Scoped actions must match the scoped-replan model.

This is a production-ready rebuild of the teacher surface, NOT patching: reuse the existing interrupt/checkpoint machinery and the single event stream — no second telemetry pipeline. High-readability, SoC, modular, testable.

## Scope

- [ ] Expand the `interrupt()` payload with, per `artifact_id`: `judge_rationale`, `revision_count`, `healing_history`, `approval_mode`.
- [ ] Add actions `approve_selected` / `reject_selected` (scoped per artifact, matching the scoped-replan issue).
- [ ] Fast-lane UI (ADR-026): auto-approve label, a **View details** affordance, and a **revert window** to undo an auto-approval.
- [ ] Live status bar that consumes the `ObservabilityEvent` stream (Phase 2 observability), with an event -> teacher-language mapping (no raw internal event names shown).
- [ ] Escalate notification + a "Needs your review" dashboard state + a single clear CTA.
- [ ] Post-export `request_revision(artifact_id, feedback)` that reuses the existing checkpoint to re-open a single artifact.

## Acceptance

- [ ] Teacher gate shows judge rationale, revision count, healing history, approval mode per `artifact_id`.
- [ ] `approve_selected` / `reject_selected` operate at artifact scope (test).
- [ ] Fast-lane label + View-details + revert window match ADR-026 (test).
- [ ] Live status bar renders solely from `ObservabilityEvent`; escalation drives "Needs your review" with one CTA.
- [ ] `request_revision(artifact_id, feedback)` reopens a single artifact via checkpoint.

## References

- ADR: `docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`
- Verdict: `docs/reports/agents/07-ux-teacher-trust-flow.md`, `docs/reports/agents/06-testing-and-observability-strategy.md`

## Depends on

- Phase 2 (observability + state), Phase 3 (judge rationale, compliance_gate_node, scoped replan), Phase 4 (escalation signals). Parent: `[Epic][Phase 5] Teacher trust UX`. See milestone `agents-hardening`.

