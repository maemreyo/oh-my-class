---
title: ComponentRegistry — single source of truth for content components
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Today the 22 content components live in **three hand-maintained places** with no single source of truth: the Pydantic discriminated union (`common/contracts/components/`), the content_creator system-prompt catalog table, and the renderer `dispatcher.html` (if/else routing). Adding a component to the union without updating the prompt → the agent can't use it; without updating the dispatcher → render fails. Questions already solve this (`contracts/questions/registry.ts` `QuestionTypeMeta` + `query()`); components do not.

Introduce a **ComponentRegistry** mirroring the question registry, as the single source of truth.

- **`ComponentMeta`** per type: `type`, `artifacts[]` (lesson/worksheet/quiz/…), `methodologies[]` (which methodology tags use it), `subjects[]`, `bloom_fit[]`, `required_fields`, `render_template`, `label_en`/`label_vi`. Defined once (Python canonical, codegen'd to TS like other contracts).
- **Derive the three consumers from it:** (a) the content_creator prompt catalog is **generated** from the registry (no hand-maintained table); (b) a **drift-guard test** asserts the Pydantic `ContentComponent` union and the renderer `dispatcher.html` cover exactly the registry's types (no missing/extra) — same pattern as the architecture manifest guard.
- Keep it **modular**: registry is a standalone module with a clean query API (issue 002 consumes it); no coupling to a specific agent.

## Acceptance criteria

- [ ] `ComponentRegistry` + `ComponentMeta` exist (Python canonical, codegen'd to TS); every one of the 22 component types is registered with metadata.
- [ ] The content_creator prompt component-catalog is generated/derived from the registry (not a hand-maintained table).
- [ ] A drift-guard test fails if the Pydantic union, the registry, and `dispatcher.html` disagree on the set of component types.
- [ ] `methodologies[]` metadata is consistent with `methodology_registry.required_components`.
- [ ] The registry exposes a query API (by artifact/methodology/subject/bloom) for issue 002.

## Detailed test suite

- [ ] `common/contracts/tests/test_component_registry.py`: all 22 union members are registered; metadata fields validate; codegen parity (Python ↔ TS).
- [ ] `tests/test_component_drift_guard.py`: registry types == Pydantic union types == `dispatcher.html` routed types; a deliberately added union member with no registry/dispatcher entry fails the guard.
- [ ] `common/contracts/tests/test_component_methodology_consistency.py`: each `methodology_registry.required_components` entry maps to a registered component with that methodology in its `methodologies[]`.
- [ ] Run `uv run pytest common/contracts/tests/test_component_registry.py tests/test_component_drift_guard.py -v` + `make check-schemas`.

## Blocked by

None - can start immediately
