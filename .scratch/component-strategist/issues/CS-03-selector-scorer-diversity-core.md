---
title: Implement standalone deterministic selector, scorer, and diversity core
status: completed
labels: [component-strategist, selector, testing]
created: 2026-07-05
---

## Parent

ADR-035 and ADR-036.

## What to build

Implement the standalone Component Strategist core as a deep module with one public planning interface: `plan_component_strategy(ComponentStrategyRequest) -> ComponentStrategyResult`. It consumes explicit request data, validated knowledge index, renderer capability manifest, optional teacher-memory adapter output, optional outcome-signal adapter output, and typed `ResearchSignals`; it returns a complete result with one recommended strategy plus up to two meaningful variants for final mode.

The deterministic core owns:

- hard filters;
- multi-signal scoring;
- provisional and final request modes;
- learning sequence assembly;
- artifact/export projection;
- diversity/cohesion rules;
- objective coverage and global budget allocation;
- evidence-balanced fallback;
- strategy quality score;
- teacher memory bounded multipliers;
- optional rationale template rendering.

LLM polish/tie-break may be represented as an adapter seam, but the deterministic path must produce a complete plan without LLM.

## Acceptance criteria

- [x] `plan_component_strategy(request) -> ComponentStrategyResult` works without LangGraph, gateway, browser, DB server, or LLM.
- [x] Provisional mode emits strategy hypotheses and typed research questions/signals needed, but does not create an approved final snapshot.
- [x] Final mode consumes typed `ResearchSignals` and may contradict provisional hypotheses when research signals justify it.
- [x] Hard filters reject artifact-incompatible, grade-incompatible, duration-incompatible, compliance-unsafe, non-renderable, and unsupported component candidates.
- [x] Selector uses renderer capability manifest and exact contract-backed component/exercise types; it never reads renderer templates or CSS.
- [x] Selector uses typed `ResearchSignals`; raw research prose is not accepted by scoring functions.
- [x] Scoring produces inspectable score breakdowns for Bloom/MOET fit, Gagne fit, objective alignment, evidence coverage, retrieval/formative presence, UDL coverage, duration fit, diversity, teacher-memory multiplier, and penalties.
- [x] Learning sequence is pack-level and move-centric, with artifact/export projections derived from it; every selected move maps to at least one objective or explicit deferred/context-only status.
- [x] Global duration/item/cognitive-load budget is allocated before per-slot budgets; slot budgets sum to a valid pack/artifact budget.
- [x] Diversity/cohesion prevents accidental same-family repetition, enforces required move coverage, and avoids repetitive prose-only strategies while allowing documented repetition for retrieval, mastery, or exam consistency.
- [x] Deterministic fallback `evidence_balanced_basic` is used only for allowed graceful-degradation cases and records an explicit fallback reason.
- [x] Result uses typed `blocked` status for domain-impossible strategy and exceptions only for programmer/config corruption.
- [x] Unit tests cover vocabulary/language, exam-prep, concept/math-science, empty teacher memory, conflicting teacher preference, no valid rich component, and no LLM adapter.
- [x] A CLI smoke command can run the selector against fixture JSON and print the selected moves/components and score summary.

## Completion evidence

- Added standalone selector in `common/contracts/component_strategy_selector.py` with scoring helpers in `common/contracts/component_strategy_selector_support.py`.
- Added selector tests in `common/contracts/tests/test_component_strategy_selector.py`.
- Added CLI smoke command `scripts/run_component_strategy_selector.py` and fixture `.scratch/component-strategist/fixtures/vocabulary_selector_request.json`.
- Verified with `uv run pytest common/contracts/tests/test_component_strategy_contracts.py common/contracts/tests/test_component_strategy_knowledge.py common/contracts/tests/test_component_strategy_selector.py`.
- Verified CLI surface with `uv run python scripts/run_component_strategy_selector.py .scratch/component-strategist/fixtures/vocabulary_selector_request.json`, which selected `contrastive_pairs` and `vocab_cluster` for `vocabulary_language`.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-02 YAML knowledge DB and SQLite index.

## References

- `docs/adr/035-component-strategist-stage.md`
- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `packages/agents/sub_agents/planner/staged_engine.py`
- `packages/agents/teaching_pack/teacher_memory.py`
- `packages/agents/teaching_pack/store_namespaces.py`
- `packages/agents/runtime.py`

## Implementation notes

- Keep the core module standalone. LangGraph state adaptation belongs in CS-04.
- Avoid special-casing strategy families in selector code; encode family behavior in metadata/scoring profiles.
- Teacher memory is a soft multiplier only. It must never override hard filters.
- Keep one engine with `provisional` and `final` modes. Do not implement separate selectors that can drift.
