---
title: Adaptive gate fast-lane by teacher trust score
status: done
labels: [gates, trust, ux, teacher-facing]
created: 2026-07-01
---

## What to build

Currently every run goes through all gates unconditionally. A teacher who has approved the `content_approval` gate unchanged on their last N consecutive runs for a specific artifact type is interrupted for a gate they will almost certainly approve immediately — adding friction, not safety.

Add an **opt-in trust-based fast-lane**: for gates where a teacher has a high approval confidence, skip the `interrupt()` and auto-approve, recording an `AUTO_APPROVED` gate response.

**Design:**

1. **Trust score** — per `(teacher_id, gate_name, artifact_type)` triple. Score = rolling window over last K gate events: `1.0` for unchanged approve, `0.5` for approved-with-minor-edit, `0.0` for reject/major-edit. Stored in BaseStore under `teacher_preferences/{teacher_id}/gate_trust`. Updated at every gate close.

2. **Fast-lane threshold** — configurable per-gate via `OMC_GATE_FAST_LANE_THRESHOLD` (default `None` = disabled). When set to a float (e.g. `0.9`), gates where the teacher's trust score for that `(gate_name, artifact_type)` ≥ threshold are auto-approved.

3. **Fast-lane mechanics** — `teacher_approval` stage node: before calling `interrupt()`, check the trust score. If above threshold: record an `AUTO_APPROVED` `GateResponse`, skip the interrupt, continue the graph. The auto-approval is visible in the event log with `visibility=TEACHER` so the teacher knows it happened.

4. **Opt-in** — `teacher.fast_lane_enabled: bool` field (or env var per-deployment). Disabled by default; teacher opts in via settings. When disabled, all gates proceed normally regardless of trust score.

5. **Override always available** — even in fast-lane, the teacher can see the auto-approved gates in the run history and request a re-review if they want to change something (standard edit/fork path via `trust-lifecycle/003`).

**Scope boundary:** fast-lane applies only to `content_approval` and `blueprint_approval` initially (the high-frequency, teacher-driven gates). `clarification_required` and `contract_confirmation` always interrupt (they need teacher input).

## Acceptance criteria

- [x] Trust score is computed and persisted to BaseStore after each gate close (all gates, even when fast-lane is off — building the trust history).
- [x] When `OMC_GATE_FAST_LANE_THRESHOLD` is set and trust score ≥ threshold: `interrupt()` is NOT called; the graph records an auto-approved approval gate state.
- [x] Auto-approval is visible in the teacher's run event log (`visibility=TEACHER`).
- [x] `clarification_required` and `contract_confirmation` always interrupt, regardless of trust score.
- [x] No fast-lane triggers when `OMC_GATE_FAST_LANE_THRESHOLD` is not set (default disabled).

## Detailed test suite

(Deterministic tests for trust-score math; real DB for gate mechanics.)

- [x] `packages/agents/tests/teaching_pack/test_gate_trust_score.py` (no LLM): seed K gate events → verify rolling trust score calculation. Verify threshold comparison.
- [x] `services/gateway/tests/test_teaching_pack_completion.py`: auto-approved content approval emits a teacher-visible `teaching_pack.content_approval.auto_approved` event before completion.
- [x] Regression: threshold not set → gate always interrupts (existing behavior unchanged).
- [x] `clarification_required` never fast-lanes even with perfect trust score.

## Verification

- 2026-07-01: `uv run pytest services/gateway/tests/test_teaching_pack_completion.py packages/agents/tests/teaching_pack/test_teacher_memory.py packages/agents/tests/teaching_pack/test_gate_trust_score.py -q` → `49 passed`.
- 2026-07-01: LSP diagnostics clean for `packages/agents/teaching_pack/gate_trust.py`, `packages/agents/teaching_pack/nodes.py`, `services/gateway/teaching_pack_completion.py`, and `services/gateway/tests/test_teaching_pack_completion.py`.

## Blocked by

- priority-upgrades/002 (teacher-class-memory) — requires BaseStore write path for gate events
- agent-interaction/002a (done ✅) — BaseStore substrate wired
