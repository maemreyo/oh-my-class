# Issue #16: [Epic][Phase 3] Core correctness — judge, compliance, harness, scoped replan

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/16
State: OPEN
Created: 2026-07-02T16:42:08Z
Updated: 2026-07-02T16:42:08Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

The core correctness surfaces of the system are fragmented. The judge/scoring logic is spread across many modules with the most complete implementation left unwired; compliance enforcement is scattered across at least five surfaces; each agent has its own ad-hoc harness; and replan wipes the entire batch instead of healing the failed artifact. This epic consolidates all four into single owners. It depends on the Phase 2 foundation (unified state + observability).

Evidence: `reviewer_node` imports the live `GEvalScorer`, NOT `AdaptiveJudge` (the 333-line, most complete, currently-unwired judge). Compliance is fragmented across `quality/layer4_judge/hard_blocks.py`, `layer3_html/html_validator.py`, `gates/presentation/answer_key_guard.py`, `config/gate_config.py`, and the `guardrail` middleware. `tools/read_file.py`, `tools/write_file.py`, `tools/task.py` are all stubs raising `NotImplementedError`; the real FS logic lives in `sub_agents/*/tools.py`.

This is a production-ready rebuild, NOT patching. Consolidations end in big-bang physical deletion of the superseded surfaces plus guard tests (see `test_no_legacy_runtime.py`); result must be high-readability, SoC, modular, testable.

## Scope

Children (separate issues in this milestone):

- [ ] Consolidate judge into `AdaptiveJudge` single entry.
- [ ] `compliance_gate_node` — deterministic policy enforcement, single owner.
- [ ] `AgentRuntime` shared harness + tool capability registry.
- [ ] Scoped replan — heal per `artifact_id`, not whole batch.

Coordination:

- [ ] An integration PR is required to fix **gate ordering**: `render_quality` -> `compliance_gate_node` -> `teacher_approval`. This ordering is the hard dependency of the ADR-026 fast-lane (auto-approve only when `compliance_gate_node` passes).

## Acceptance

- [ ] All four child issues closed with guard/contract tests green.
- [ ] Gate ordering integration test proves `render_quality -> compliance_gate_node -> teacher_approval`.
- [ ] No live path imports `GEvalScorer` or binds a non-IMPLEMENTED tool.

## References

- ADR: `docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`, `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/03-quality-judge-consolidation.md`, `docs/reports/agents/04-agent-harness-tool-contracts.md`

## Depends on

- Phase 2 (`[Epic][Phase 2] State unification + observability backbone`) — needs unified state + event bus. See milestone `agents-hardening`.

