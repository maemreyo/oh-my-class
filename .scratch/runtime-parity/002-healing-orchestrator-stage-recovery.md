---
title: Wire the healing orchestrator into the teaching-pack runtime
status: done
labels: []
created: 2026-06-30
---

## What to build

The teaching-pack runtime only has scoped regeneration (reject → `artifact_workflow`); the sophisticated 5-strategy healing (`retry → rewrite → reroute → replan → escalate`) in `packages/agents/healing/orchestrator.py` is wired only to the FROZEN legacy graph. A `max_healing_attempts` config exists in `teaching_pack/config.py` but is unused.

- Adapt `HealingOrchestrator.heal()` (operates on `OhMyClassState`) to the teaching-pack state via a thin adapter, or refactor it to a state-agnostic core.
- Add a recovery hook in `quality_routing` (`packages/agents/teaching_pack/quality_routing.py`): when the 6-layer gate (parity issue 001) fails, select a healing strategy (rewrite → reroute → replan) bounded by `max_healing_attempts`, then escalate to the teacher gate when exhausted.
- `generation_model` override (reroute to a different model) flows through the existing LLM transport.
- Distinguish failure types (validation / content / score / timeout) to pick the strategy, mirroring the legacy `fail_type` semantics.

## Acceptance criteria

- [x] `quality_routing` invokes the healing orchestrator on gate failure (not scoped-regeneration only), bounded by `max_healing_attempts`.
- [x] Strategies escalate in order (rewrite → reroute → replan → escalate) and `reroute` switches the generation model.
- [x] On exhaustion the run escalates to the teacher (or fails closed) — never silently emits a low-quality pack.
- [x] `max_healing_attempts` config is honored (no longer dead config).
- [x] Existing scoped-regeneration (teacher-reject loop) still works.

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [x] `packages/agents/teaching_pack/tests/test_healing_recovery.py`: a gate failure triggers rewrite; a persistent model-specific failure triggers reroute (model switches); structural failure triggers replan.
- [x] same file: after `max_healing_attempts`, the run escalates to the teacher gate / fails closed — no low-quality pack is emitted.
- [x] same file: `max_healing_attempts=0` disables healing and falls back to current behavior.
- [x] Regression: the teacher-reject scoped-regeneration loop is unchanged.
- [x] Run `uv run pytest packages/agents/teaching_pack/tests/test_healing_recovery.py -v`.

## Blocked by

- .scratch/runtime-parity/001-six-layer-quality-gate-adapter.md
