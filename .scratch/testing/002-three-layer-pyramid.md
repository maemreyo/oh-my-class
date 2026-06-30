---
title: Three-layer test pyramid — per-agent, seam/handoff, E2E
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Structure system tests as a pyramid over the **authoritative teaching-pack stage runtime** (not the legacy graph). All LLM-touching levels use the real LLM via 9router (`real_llm` tier); structural assertions are deterministic.

- **Per-agent (real-LLM behavior)**: each agent node (`planner_node`, `researcher_node`, `content_creator_node`, reviewer, `unit_planner`, `sequence_critic`) tested with real LLM for behavior/quality; deterministic assertions on output shape/contract.
- **Seam/handoff (integration)**: data flowing **between stages** — `setup_contract → planning_blueprint → post_blueprint_research → artifact_workflow → render_quality → teacher_approval → export_finalize`, plus the `plan_unit` branch handoffs (triage→unit_planner→gate→unit_prep→fan-out→child). Assert the contract at each seam (the producer's output validates as the consumer's input).
- **E2E (full pipeline)**: a real run from request → approved exported pack, through the real stage graph + worker + job store + real LLM.

This issue defines the pyramid structure and the seam/E2E levels; per-feature epics contribute their own per-agent tests on this scaffold.

## Acceptance criteria

- [ ] Per-agent tests exist for every agent node, real-LLM for behavior + deterministic for contract shape.
- [ ] Seam tests assert producer-output ⊆ consumer-input contract at every stage boundary (single-lesson and `plan_unit`).
- [ ] At least one full E2E test runs request → exported pack through the real stage runtime + worker + real LLM.
- [ ] Tests target the teaching-pack stage runtime, never `build_oh_my_class_graph`.
- [ ] LLM-touching tests are `real_llm`-marked; seam contract checks are deterministic where possible.

## Detailed test suite

(Real DB + real LLM via 9router `:20228` / `4omc`.)

- [ ] `tests/agents/test_per_agent_behavior.py`: each agent produces a contract-valid, behaviorally-correct output for a representative input.
- [ ] `tests/integration/test_stage_seams.py`: each stage's output validates as the next stage's input; a deliberately corrupted handoff is caught.
- [ ] `tests/e2e/test_full_pipeline.py`: a single-lesson request runs end-to-end to an approved exported pack.
- [ ] `tests/e2e/test_full_unit_pipeline.py`: a `plan_unit` request runs through unit gate → fan-out → child packs (see topic-decomposition 019 for the full unit scenario).
- [ ] Run `uv run pytest -m real_llm tests/integration/test_stage_seams.py tests/e2e/test_full_pipeline.py -v`.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
