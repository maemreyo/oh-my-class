# Issue #31: [RFC] Localization agent (multilingual artifacts)

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/31
State: OPEN
Created: 2026-07-02T16:43:05Z
Updated: 2026-07-02T16:43:05Z
Labels: enhancement, agents-refactor, rfc
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Completion notes

- Landed Localization RFC at `docs/rfc/localization-agent.md`.
- RFC enumerates renderer, `theme.json`, contract i18n fields, `AgentRuntime`, and acceptance tests.

## Body

## Context

A Localization agent would produce multilingual artifacts. This is **Priority 2** of the new-agent effort and, like all new agents, is built only **after** the foundation (unified state, observability, shared `AgentRuntime`). It touches the renderer, `theme.json`, and the contracts (adding i18n fields) — a cross-cutting change that needs its own RFC.

This is a production-ready build, NOT patching: it hangs off `AgentRuntime` and follows SoC/modularity/testability. As an RFC it starts as its own design doc.

## Scope

- [ ] Write the Localization RFC / design doc.
- [ ] Design the agent on the shared `AgentRuntime` — no bespoke harness.
- [ ] Specify renderer changes required to emit localized artifacts.
- [ ] Specify `theme.json` changes for locale-aware theming.
- [ ] Specify contract changes: add i18n fields to the artifact contracts.
- [ ] Scope acceptance/tests in the RFC (real-LLM tests, 9router :20228 / model 4omc).

## Acceptance

- [x] RFC design doc reviewed/accepted before implementation.
- [x] Renderer, `theme.json`, and contract i18n-field changes enumerated in the RFC.
- [x] Design builds on `AgentRuntime`.

## References

- ADR: `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/04-agent-harness-tool-contracts.md`, `docs/reports/agents/08-migration-roadmap.md`

## Depends on

- Foundation complete: Phase 2 + Phase 3 `AgentRuntime`. Priority 2 of 3 new-agent RFCs (after Researcher, before Accessibility). See milestone `agents-hardening`.
