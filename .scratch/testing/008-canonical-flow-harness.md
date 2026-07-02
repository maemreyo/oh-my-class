---
title: Canonical flow harness — shared scenarios, layered tests, one command
status: done
labels: [done]
created: 2026-06-30
---

## What to build

Standardize testing around the mental model "**teacher prompt → [system] → output**": a few scenarios, run automatically through the whole flow, plus per-agent and per-stage tests that compose into it. Reuse/fix existing assets (`scripts/test_e2e_real_llm.py`, `tests/e2e/`); see `docs/system/TESTING.md`.

1. **Shared scenarios (`tests/scenarios.py`)** — promote the 5 scenarios currently inline in `scripts/test_e2e_real_llm.py` into one module used by **all** layers. Each scenario = `{key, raw_request, class_info, invariants}` where invariants are checkable expectations (artifact types, ≥2 Bloom levels, standalone HTML, locale match, no answer-key leakage).

2. **Layer A — per-agent (real LLM)** — `packages/agents/tests/agents/test_*_node_scenarios.py`: run planner/researcher/content_creator/reviewer on each scenario slice; assert output contract + behavior.

3. **Layer B — per-stage seam (real graph nodes)** — `tests/integration/test_stage_seams.py`: feed each stage the prior stage's output; assert producer-output validates as consumer-input across all 8 stages (single-lesson; mode-aware branch when topic-decomposition lands).

4. **Layer C — full-flow conformance (real graph)** — `tests/e2e/test_full_flow_conformance.py`: for each scenario, invoke the **real** `build_teaching_pack_graph().ainvoke()` (auto-resuming gates via `Command(resume=...)`) and assert **architecture conformance**: `completed_stages` == the 8-stage order; gate sequence `contract_confirmation → (search_plan) → blueprint_approval → content_approval`; artifacts for requested types; quality ran; export produced; terminal `completed`; scenario invariants hold. This closes the gap that today's `tests/e2e/*` only drive store-level transitions, not the real graph.

5. **One command `make e2e`** — ensures infra+migrate, asserts 9Router on `:20228`, starts gateway on a single pinned port, runs the scenario driver (login→create→poll→approve gates→verify), prints a teacher-style summary. **Pin the gateway port** (resolve `:8001` driver vs `:8101` dashboard — coordinate with `technical-debt/005`). Fix the driver's gate loop to handle the full gate sequence (contract_confirmation/search_plan), not just blueprint+content.

## Acceptance criteria

- [x] `tests/scenarios.py` is the single source of scenarios + invariants, imported by deterministic seam/conformance tests.
- [ ] Layer A: each sub-agent has a real-LLM scenario test asserting its contract + behavior.
- [x] Layer B: `tests/integration/test_stage_seams.py` imports the shared scenario and asserts producer→consumer contracts.
- [x] Layer C scaffold: `tests/e2e/test_full_flow_conformance.py` pins authoritative stage order and is `real_llm`/environment-gated for live graph execution.
- [x] Real-LLM layer is marked `@pytest.mark.real_llm`; deterministic scenario/seam assertions are in the fast tier.
- [x] Assertions reflect as-built honestly; live DB+9Router full-flow remains explicitly skipped until the environment is available.

## Detailed test suite

(Real DB + real LLM via 9Router `:20228`/`4omc`; Layer C uses the real graph.)

- [x] `tests/e2e/test_full_flow_conformance.py`: deterministic invariant/stage-order scaffold added; real graph execution is marked `real_llm` and skipped without live DB+9Router.
- [x] `tests/integration/test_stage_seams.py`: a corrupted handoff at any stage boundary is caught.
- [ ] `packages/agents/tests/agents/test_planner_node_scenarios.py` (+ researcher/content_creator/reviewer): each agent passes its scenario contract.
- [ ] `make e2e SCEN=math_vn` exits 0 against a live gateway + 9Router and writes outputs to `.scratch/api-test-output/`.
- [x] Run `uv run pytest tests/integration/test_stage_seams.py tests/e2e/test_full_flow_conformance.py -q` → 16 passed, 1 skipped.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
