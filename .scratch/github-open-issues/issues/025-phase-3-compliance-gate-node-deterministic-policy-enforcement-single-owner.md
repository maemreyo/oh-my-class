# Issue #25: [Phase 3] compliance_gate_node — deterministic policy enforcement, single owner

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/25
State: OPEN
Created: 2026-07-02T16:42:41Z
Updated: 2026-07-02T16:42:41Z
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

Compliance / policy enforcement is fragmented across at least five surfaces: `quality/layer4_judge/hard_blocks.py`, `layer3_html/html_validator.py`, `gates/presentation/answer_key_guard.py`, `config/gate_config.py`, and the `guardrail` middleware. No single owner means rules drift, overlap, and can silently disagree. We need one deterministic, non-LLM node that owns hard-block policy, PII, and answer-key leakage.

This node is the **hard dependency of the ADR-026 fast-lane**: auto-approve is only allowed when `compliance_gate_node` passes.

This is a production-ready rebuild, NOT patching: consolidate the scattered checks into one node, then delete/neutralize the duplicated enforcement at the old surfaces with guard tests (repo precedent `test_no_legacy_runtime.py`). Deterministic, high-readability, SoC, modular, testable.

## Scope

- [ ] Create `compliance_gate_node` — a **non-LLM**, deterministic node consolidating the 9 hard-blocks + PII detection + answer-key leakage checks from the 5 fragmented surfaces.
- [ ] Wire it into the graph **after `render_quality`, before `teacher_approval`** (gate ordering owned by the Phase 3 integration PR).
- [ ] Make it the sole owner: remove/route the duplicated enforcement out of `hard_blocks.py`, `html_validator.py`, `answer_key_guard.py`, `gate_config.py`, and the `guardrail` middleware.
- [ ] Reconcile with ADR-018's `SixLayerQualityGate` so there is no duplicated responsibility.
- [ ] One test per hard-block, exercised through the **real production path** (not unit-only).
- [ ] Emit an `ObservabilityEvent` (Phase 2) on each block, carrying a teacher-readable reason for the Phase 5 gate.

## Acceptance

- [ ] `compliance_gate_node` runs deterministically between `render_quality` and `teacher_approval`.
- [ ] Each of the 9 hard-blocks + PII + answer-key leakage has a passing test through the production path.
- [ ] No other surface independently enforces these blocks (guard test).
- [ ] Fast-lane auto-approve is gated on this node passing (ADR-026).

## References

- ADR: `docs/adr/026-fast-lane-teacher-gate-and-invariant-06.md`, `docs/adr/018-runtime-parity-and-legacy-decommission.md`
- Verdict: `docs/reports/agents/03-quality-judge-consolidation.md`, `docs/reports/agents/07-ux-teacher-trust-flow.md`

## Depends on

- `[Epic][Phase 3] Core correctness` (parent), Phase 2 observability (`[Phase 2] Observability backbone`) for block events. Blocks the ADR-026 fast-lane and the Phase 5 gate. See milestone `agents-hardening`.

