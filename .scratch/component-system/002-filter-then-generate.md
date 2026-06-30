---
title: Filter-then-generate — give content_creator a context-focused component catalog
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Improve component selection from "agent sees the whole hand-listed catalog" to **filter-then-generate**: a deterministic pre-step queries the `ComponentRegistry` (issue 001) for the components relevant to the current context, and the agent generates within that focused, always-valid, always-complete subset. No semantic search — a precise metadata filter; the LLM still composes (it is good at that).

- A `select_components(artifact_type, methodology_tags, subject, bloom_levels) -> list[ComponentMeta]` query (registry API) producing the relevant subset, **always including** the methodology `required_components` (must-have) and the artifact-type baseline.
- `content_creator` receives this filtered catalog (generated into its prompt) instead of the full static list — fewer, more-relevant options → better selection, less noise, and impossible to reference a component invalid for the context.
- Output still validated against the Pydantic union + methodology required-components gate (unchanged). The filter is an aid, not a second enforcement layer.
- Modular: the selection step is standalone and testable; it does not hardcode component knowledge (all from the registry).

## Acceptance criteria

- [ ] `select_components(...)` returns the context-relevant subset, always including methodology required-components and artifact baseline.
- [ ] `content_creator`'s prompt catalog is the filtered subset for the run's `(artifact_type, methodology, subject)`, derived from the registry.
- [ ] A component irrelevant to the context is absent from the catalog; required-components are always present.
- [ ] Output validation + methodology gate are unchanged (filter is an aid, not enforcement).
- [ ] Selection is deterministic and standalone (no LLM, no hardcoded component list).

## Detailed test suite

(Deterministic for the filter; real LLM for the generation integration.)

- [ ] `packages/agents/tests/test_select_components.py`: for `(quiz, why_wrong_reasoning, math)` the subset includes `question_card` + `wrong_reasons` (required) and excludes irrelevant components (e.g. `film_clip_activity`).
- [ ] same file: methodology required-components are always present even if not "relevant" by other criteria.
- [ ] `packages/agents/tests/test_content_creator_filtered_catalog.py` (real LLM): content_creator generates only components from the filtered catalog; output passes the union + methodology gate.
- [ ] Run `uv run pytest packages/agents/tests/test_select_components.py -v` + the real-LLM integration nightly.

## Blocked by

- .scratch/component-system/001-component-registry-single-source.md
