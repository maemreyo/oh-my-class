# Issue #32: [RFC] Accessibility agent (alt-text / reading-level / WCAG)

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/32
State: OPEN
Created: 2026-07-02T16:43:08Z
Updated: 2026-07-02T16:43:08Z
Labels: enhancement, agents-refactor, rfc
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Completion notes

- Landed Accessibility RFC at `docs/rfc/accessibility-agent.md`.
- RFC maps all output to `ArtifactContent.accessibility`, defines WCAG/reading-level checks, and requires `AgentRuntime`.

## Body

## Context

An Accessibility agent would generate alt-text, control reading-level, and enforce WCAG on artifacts. This is **Priority 3** of the new-agent effort and is built only **after** the foundation (unified state, observability, shared `AgentRuntime`). It maps cleanly onto the existing `ArtifactContent.accessibility` field, so the contract surface already exists.

This is a production-ready build, NOT patching: it hangs off `AgentRuntime` and follows SoC/modularity/testability. As an RFC it starts as its own design doc.

## Scope

- [ ] Write the Accessibility RFC / design doc.
- [ ] Design the agent on the shared `AgentRuntime` — no bespoke harness.
- [ ] Map outputs to the existing `ArtifactContent.accessibility` field (alt-text, reading-level, WCAG results).
- [ ] Define WCAG checks and reading-level targets to enforce.
- [ ] Scope acceptance/tests in the RFC (real-LLM tests, 9router :20228 / model 4omc).

## Acceptance

- [x] RFC design doc reviewed/accepted before implementation.
- [x] Design writes to `ArtifactContent.accessibility` (no new parallel field).
- [x] Design builds on `AgentRuntime`.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/04-agent-harness-tool-contracts.md`, `docs/reports/agents/07-ux-teacher-trust-flow.md`

## Depends on

- Foundation complete: Phase 2 + Phase 3 `AgentRuntime`. Priority 3 of 3 new-agent RFCs (after Researcher and Localization). See milestone `agents-hardening`.
