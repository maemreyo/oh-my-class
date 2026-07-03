# Issue #25: [Phase 3] compliance_gate_node — deterministic policy enforcement, single owner

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/25
State: OPEN
Created: 2026-07-02T16:42:41Z
Updated: 2026-07-02T16:42:41Z
Labels: enhancement, agents-refactor, phase-3
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Progress notes

- Added `StageEnum.COMPLIANCE_GATE` and inserted `compliance_gate` between `render_quality` and `teacher_approval` in the teaching-pack stage graph.
- Changed successful `route_after_render_quality()` output from `teacher_approval` to `compliance_gate`.
- Added `route_after_compliance_gate()` so failed compliance blocks route back to `artifact_workflow`, not teacher approval.
- Added deterministic `packages/agents/teaching_pack/compliance.py` node logic:
  - emits `hard_block_violation` `ObservabilityEvent` entries with teacher-readable reasons;
  - returns `compliance_passed`, `compliance_result`, failure context, and recovery route;
  - evaluates artifacts and rendered snapshots without LLMs.
- Added single policy owner in `packages/quality/compliance_policy.py` for hard-block codes, HTML policy checks, answer-key leakage checks, and HTML accessibility hard blocks.
- Neutralized/delegated old duplicated enforcement surfaces:
  - `packages/quality/layer4_judge/hard_blocks.py` now delegates hard-block classification to compliance policy.
  - `packages/quality/layer3_html/html_validator.py` now delegates policy checks to compliance policy.
  - `packages/agents/gates/presentation/answer_key_guard.py` now delegates answer-key checking to compliance policy.
  - `packages/agents/gates/presentation/html_validator.py` now delegates doctype/external-asset checks to compliance policy and no longer exposes hard-block disable toggles.
  - `packages/agents/config/gate_config.py` no longer owns hard-block toggles.
  - `packages/agents/middleware/safety/guardrail.py` no longer independently blocks PII; compliance gate owns deterministic policy.
- Fast-lane content approval now requires `state["compliance_passed"] is True` before considering trust-score auto-approval.
- Added production-path tests for all HTML hard blocks, PII leakage, answer-key leakage, observability emission, compliance routing, and fast-lane gating.
- Added guard test `packages/agents/tests/test_no_legacy_compliance_policy.py` to prevent legacy surfaces from regaining independent hard-block policy ownership.
- Post-review cleanup removed the remaining unused/delegated legacy ownership remnants:
  - removed duplicate text collection from `packages/agents/gates/presentation/answer_key_guard.py`;
  - removed local `EXTERNAL_ASSET_PATTERNS` / `HARD_BLOCKS` ownership from `packages/quality/layer3_html/html_validator.py`;
  - updated `packages/quality/tests/test_judge_interface.py` to assert hard-block overlap against `packages/quality/compliance_policy.py`;
  - expanded the legacy-policy guard to cover the Layer-3 validator and exact owner symbol names;
  - refreshed stale compliance ownership docs in `AGENTS.md`, `docs/system/ARCHITECTURE.md`, and `docs/reports/core/02-quality-gate-harnessing.md`.

## Verification evidence

- `uv run pytest packages/agents/tests/teaching_pack/test_foundation.py packages/agents/tests/teaching_pack/test_nodes.py packages/agents/tests/teaching_pack/test_render_quality.py packages/quality/tests/test_layer3_html.py packages/quality/tests/test_judge_interface.py packages/agents/tests/test_no_legacy_compliance_policy.py packages/agents/config/tests/test_gate_config.py packages/agents/gates/tests/test_quality_gates.py -q` → `226 passed`.
- Post-review rerun of the same focused command → `226 passed`.
- Legacy-owner search after cleanup returned no matches in live docs/legacy surfaces for `HARD_BLOCKS =`, `EXTERNAL_ASSET_PATTERNS`, stale hard-block snippets, or old post-render/answer-key ownership phrasing.
- LSP diagnostics clean for changed Issue #25 Python files checked:
  - `packages/agents/teaching_pack/compliance.py`
  - `packages/quality/compliance_policy.py`
  - `packages/agents/teaching_pack/nodes.py`
  - `packages/agents/teaching_pack/graph.py`
  - `packages/agents/teaching_pack/stages.py`
  - `packages/agents/teaching_pack/quality_routing.py`
  - `packages/quality/layer3_html/html_validator.py`
  - `packages/quality/layer4_judge/hard_blocks.py`
  - `packages/agents/gates/presentation/answer_key_guard.py`
  - `packages/agents/gates/presentation/html_validator.py`
  - `packages/agents/gates/content_reviewer.py`
  - `packages/agents/middleware/safety/guardrail.py`
  - `packages/agents/config/gate_config.py`
  - `packages/agents/tests/test_no_legacy_compliance_policy.py`
- Manual smoke through the compliance node surface:
  - passing content returned `compliance_passed=True` and routed to `teacher_approval`;
  - failing PII/answer-key content returned `compliance_passed=False`, routed to `artifact_workflow`, and emitted `hard_block_violation` events.
- Post-review manual smoke via `uv run .scratch/smoke_compliance_gate.py` → `24/24 passed`, covering render-quality routing, valid pass, missing doctype, external CDN, PII, student answer-key leakage, hard-block observability payloads, teacher-only answer keys, and no pass-path hard-block events.
- Size audit performed on changed files. Pre-existing large files remain large (`nodes.py`, `test_nodes.py`, `test_quality_gates.py`); no broad refactor was mixed into this issue.

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
