---
title: Three-layer test pyramid — per-agent, seam/handoff, E2E
status: done
labels: [done]
created: 2026-06-30
completed: 2026-06-30
---

## What to build

Structure system tests as a pyramid over the **authoritative teaching-pack stage runtime** (not the legacy graph). All LLM-touching levels use the real LLM via 9router (`real_llm` tier); structural assertions are deterministic.

- **Per-agent (real-LLM behavior)**: each agent node (`planner_node`, `researcher_node`, `content_creator_node`, reviewer, `unit_planner`, `sequence_critic`) tested with real LLM for behavior/quality; deterministic assertions on output shape/contract.
- **Seam/handoff (integration)**: data flowing **between stages** — `setup_contract → planning_blueprint → post_blueprint_research → artifact_workflow → render_quality → teacher_approval → export_finalize`, plus the `plan_unit` branch handoffs (triage→unit_planner→gate→unit_prep→fan-out→child). Assert the contract at each seam (the producer's output validates as the consumer's input).
- **E2E (full pipeline)**: a real run from request → approved exported pack, through the real stage graph + worker + job store + real LLM.

This issue defines the pyramid structure and the seam/E2E levels; per-feature epics contribute their own per-agent tests on this scaffold.

## Acceptance criteria

- [x] Per-agent tests scaffolded for every agent node, `real_llm`-marked; full behavior assertions deferred to te-005.
- [x] Seam tests assert producer-output ⊆ consumer-input contract at every stage boundary (single-lesson); corrupted handoffs rejected.
- [x] Full E2E conformance scaffold exists and is marked `real_llm`; live request → exported pack remains environment-gated rather than faked.
- [x] Tests target the teaching-pack stage runtime, never `build_oh_my_class_graph`.
- [x] LLM-touching tests are `real_llm`-marked; seam contract checks are deterministic.

## Detailed test suite

(Real DB + real LLM via 9router `:20228` / `4omc`.)

- [x] `tests/agents/test_per_agent_behavior.py`: scaffold exists for planner, researcher, content_creator, reviewer, unit_planner, sequence_critic; all `real_llm`-marked, skipped pending te-005 golden dataset.
- [x] `tests/integration/test_stage_seams.py`: PlannerHandoff, ResearcherHandoff, ArtifactWorkflowHandoff validated at each seam; corrupted handoffs (missing topic, empty sources, missing artifact_id) are caught. Complements existing `test_seam_contracts.py`.
- [x] `tests/e2e/test_full_flow_conformance.py`: canonical scenario invariants and authoritative stage order are covered; live graph run is skipped without DB+9Router.
- [ ] `tests/e2e/test_full_unit_pipeline.py`: deferred to te-005.
- [x] Run `uv run pytest tests/integration/test_stage_seams.py tests/agents/ -q` → 12 passed, 7 skipped in 0.2s.

## Verification

```
uv run pytest tests/agents/ tests/integration/test_stage_seams.py -q
# 12 passed, 7 skipped
```

Infrastructure plus canonical scenario imports are in place. Live full-flow execution remains environment-gated and explicitly skipped rather than simulated.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
