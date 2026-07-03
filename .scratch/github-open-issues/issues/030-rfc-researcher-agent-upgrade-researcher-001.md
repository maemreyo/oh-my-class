# Issue #30: [RFC] Researcher agent upgrade (researcher-001)

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/30
State: OPEN
Created: 2026-07-02T16:43:03Z
Updated: 2026-07-02T16:43:03Z
Labels: enhancement, agents-refactor, rfc
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Completion notes

- Landed local `researcher-001` recommendation spec and RFC at `docs/rfc/researcher-001-upgrade.md`.
- RFC requires `AgentRuntime`, `AGENT_CAPABILITIES`, 9Router `:20228` model `4omc`, source provenance, and FACT claim verification.

## Body

## Context

New-agent work begins only **after** the foundation is in place — unified state, observability backbone, and the shared `AgentRuntime`. The Researcher agent upgrade is **Priority 1** of the new-agent effort. Its source material is the `researcher-001` agent recommendation set, which is **not yet a document in this repo** — so the first task is to locate/produce that spec before designing anything.

This is a production-ready build, NOT patching: it hangs off the shared `AgentRuntime` (Phase 3) and follows SoC/modularity/testability. As an RFC, it starts as its own design doc, not code.

## Scope

- [ ] Locate or produce the `researcher-001` recommendation spec and land it as a doc in the repo (it does not exist yet).
- [ ] Write the RFC / design doc for the Researcher agent upgrade based on that spec.
- [ ] Design the agent to build on the shared `AgentRuntime` (retry/backoff, cost tagging, streaming, tool capability registry) — no bespoke harness.
- [ ] Define tool capabilities via `AGENT_CAPABILITIES`; nothing non-IMPLEMENTED bound.
- [ ] Scope acceptance/tests as part of the RFC (real-LLM tests, 9router :20228 / model 4omc).

## Acceptance

- [x] `researcher-001` spec exists in the repo.
- [x] RFC design doc reviewed/accepted before implementation begins.
- [x] Design explicitly builds on `AgentRuntime` and the capability registry.

## References

- ADR: `docs/adr/017-topic-decomposition-and-unit-fan-out.md`, `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/04-agent-harness-tool-contracts.md`, `docs/reports/agents/08-migration-roadmap.md`

## Depends on

- Foundation complete: Phase 2 (state + observability) and Phase 3 `AgentRuntime` (`[Phase 3] AgentRuntime shared harness`). Priority 1 of 3 new-agent RFCs (before Localization, Accessibility). See milestone `agents-hardening`.
