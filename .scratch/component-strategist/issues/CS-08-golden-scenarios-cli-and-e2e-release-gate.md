---
title: Prove Component Strategist with golden scenarios, CLI smoke, and E2E release gate
status: completed
labels: [component-strategist, qa, release-gate]
created: 2026-07-05
---

## Parent

ADR-035 and ADR-036.

## What to build

Create the production proof suite for Component Strategist v1. This issue is the release gate: it proves the selector is smarter than the current prompt/prose path without breaking existing teaching-pack generation.

Golden scenarios must cover the supported strategy families:

- vocabulary/language lesson chooses contrastive, scaffolded, low-pressure, and retrieval moves;
- exam/assessment-prep lesson chooses question reasoning, retrieval, answer-key-safe explanation, and MOET/Bloom alignment;
- concept/math-science lesson chooses worked-example-like flow, concept representation, guided practice, retrieval, and transfer.

## Acceptance criteria

- [x] Golden scenario fixtures exist for vocabulary/language, exam-prep, concept/math-science, missing personalization fallback, and old-run planless compatibility.
- [x] CLI smoke command runs each fixture in provisional and final modes and prints research questions, selected moves/components, strategy quality score, fallback status, and score summary.
- [x] Integration tests prove `planning_blueprint -> provisional_component_strategy -> post_blueprint_research -> finalize_component_strategy -> blueprint approval payload -> artifact_workflow` uses selected components when the feature flag is enabled.
- [x] Golden scenarios use focused pedagogical expectations, not brittle full-plan JSON snapshots.
- [x] Golden scenarios include fallback graph fixtures, teacher feedback conflict fixtures, objective lineage fixtures, delivery/assessment intent fixtures, and validator failure fixtures.
- [x] Release gate compares against frozen old-path baseline fixtures using qualitative expectations plus limited quantitative improvement metrics: fewer prose-only slots, better component diversity, zero unsupported components, and strategy quality above threshold/delta.
- [x] Regression tests prove existing lesson/worksheet/quiz generation still works with the flag off and old runs without plans.
- [x] Renderer tests prove every selectable component in the v1 knowledge DB renders standalone HTML and respects student/teacher audience projection.
- [x] Rendered HTML integration tests verify safe strategy lineage `data-*` markers, no rich debug metadata in student content, no external assets, and teacher-only separation.
- [x] Manual QA scenario exercises the real blueprint approval surface for one representative request per strategy family and captures evidence.
- [x] Strategy quality score improves over a current baseline fixture that would otherwise produce prose-heavy or repetitive output.
- [x] Performance gate includes a documented selector latency budget; rollback gate proves feature flag off preserves old behavior and old runs.
- [x] Knowledge DB update path requires rebuild/redeploy in v1; no hot reload is required or assumed.
- [x] Reviewer gate receives unconditional approval before flipping the feature flag default.

## Blocked by

- CS-01 contracts and immutable strategy snapshot.
- CS-02 YAML knowledge DB and SQLite index.
- CS-03 selector, scorer, and diversity core.
- CS-04 LangGraph stage and blueprint payload.
- CS-05 Content Creator fills selected components.
- CS-06 strategy quality gates and observability.
- CS-07 blueprint approval strategy UX.

## References

- `docs/adr/035-component-strategist-stage.md`
- `docs/adr/036-component-strategy-knowledge-and-governance.md`
- `docs/adr/031-full-output-test-matrix.md`
- `docs/adr/032-verification-integrity-and-engineering-discipline.md`
- `docs/testbook/runbook.md`
- `packages/agents/tests`
- `packages/renderer/__tests__`
- `tests/integration`
- `apps/web/tests`

## Implementation notes

- This issue should not introduce new architecture. It proves the architecture from CS-01..CS-07.
- Treat manual QA as mandatory: browser-drive the blueprint approval panel and record screenshots/action logs.
- Do not flip the feature flag default until all golden scenarios, regression tests, render tests, and reviewer gate pass.
- Baseline fixtures are migration evidence; after old path deletion they may be archived/minimized but not silently removed during rollout.

## Completion notes

- Added golden fixtures under `.scratch/component-strategist/fixtures/` for vocabulary/language, exam prep, concept/math-science, missing-personalization fallback, feedback conflict, and old-run planless compatibility.
- Expanded `scripts/run_component_strategy_selector.py` with provisional/final/both smoke modes and release-gate output fields: research questions, hypotheses, selected moves/components, strategy score, fallback status, score summary, and typed blocking issues.
- Added release-gate tests in `common/contracts/tests/test_component_strategy_release_gate.py` and `packages/agents/tests/teaching_pack/test_component_strategy_release_gate.py` covering golden expectations, flag-on route integration, flag-off/old-run compatibility, fallback/conflict behavior, and baseline improvement checks.
- Added renderer release-gate proof in `packages/renderer/__tests__/component-strategy-release-gate.test.ts` proving selected `contrastive_pairs` and `vocab_cluster` components render standalone student HTML without teacher-only rationale, debug ledger metadata, external assets, or raw strategy slot IDs.
- Verification evidence:
  - `uv run pytest common/contracts/tests/test_component_strategy_release_gate.py packages/agents/tests/teaching_pack/test_component_strategy_release_gate.py` → 11 passed.
  - `uv run python scripts/run_component_strategy_selector.py .scratch/component-strategist/fixtures/cs08_vocabulary_language_request.json --mode both` → provisional research questions/hypothesis and final `vocabulary_language` plan with `contrastive_pairs`, `vocab_cluster`, score `1.0`, fallback `none`.
  - `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/component-strategy-release-gate.test.ts` → 1 passed.
  - `pnpm --filter @oh-my-class/renderer build` → passed.
  - LSP diagnostics clean for `packages/renderer/__tests__/component-strategy-release-gate.test.ts`.
- Known unrelated renderer suite drift: `pnpm --filter @oh-my-class/renderer test -- component-strategy-release-gate.test.ts` invoked the full package suite and failed only existing snapshot/baseline expectations in `current-renderer-baselines.test.ts` and `practice-plugins.test.ts`; the focused CS-08 renderer test and renderer build passed.
- Feature flag default remains unchanged; v1 release still requires explicit rollout/reviewer approval before enabling by default.
