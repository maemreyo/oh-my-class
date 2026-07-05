---
title: Prove Component Strategist with golden scenarios, CLI smoke, and E2E release gate
status: ready-for-agent
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

- [ ] Golden scenario fixtures exist for vocabulary/language, exam-prep, concept/math-science, missing personalization fallback, and old-run planless compatibility.
- [ ] CLI smoke command runs each fixture in provisional and final modes and prints research questions, selected moves/components, strategy quality score, fallback status, and score summary.
- [ ] Integration tests prove `planning_blueprint -> provisional_component_strategy -> post_blueprint_research -> finalize_component_strategy -> blueprint approval payload -> artifact_workflow` uses selected components when the feature flag is enabled.
- [ ] Golden scenarios use focused pedagogical expectations, not brittle full-plan JSON snapshots.
- [ ] Golden scenarios include fallback graph fixtures, teacher feedback conflict fixtures, objective lineage fixtures, delivery/assessment intent fixtures, and validator failure fixtures.
- [ ] Release gate compares against frozen old-path baseline fixtures using qualitative expectations plus limited quantitative improvement metrics: fewer prose-only slots, better component diversity, zero unsupported components, and strategy quality above threshold/delta.
- [ ] Regression tests prove existing lesson/worksheet/quiz generation still works with the flag off and old runs without plans.
- [ ] Renderer tests prove every selectable component in the v1 knowledge DB renders standalone HTML and respects student/teacher audience projection.
- [ ] Rendered HTML integration tests verify safe strategy lineage `data-*` markers, no rich debug metadata in student content, no external assets, and teacher-only separation.
- [ ] Manual QA scenario exercises the real blueprint approval surface for one representative request per strategy family and captures evidence.
- [ ] Strategy quality score improves over a current baseline fixture that would otherwise produce prose-heavy or repetitive output.
- [ ] Performance gate includes a documented selector latency budget; rollback gate proves feature flag off preserves old behavior and old runs.
- [ ] Knowledge DB update path requires rebuild/redeploy in v1; no hot reload is required or assumed.
- [ ] Reviewer gate receives unconditional approval before flipping the feature flag default.

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
