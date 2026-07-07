---
title: Real schema-bound LLM call in ContentMaterializer
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, llm]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 1)

## What to build

`SlideDeckEngine`'s `ContentMaterializer` phase currently makes zero LLM calls (`llm_calls=0` is a hardcoded literal in `SlideDeckTraceMetadata`; no phase file references `llm_client`). Wire a real, schema-bound LLM call into this phase only — wording, examples, and activity text are LLM-authored; every other phase (`PedagogicalPlanner`, `SlideArchitecturePlanner`, `LayoutComposer`, `InteractionPlanner`, density/accessibility/export auditors) stays fully deterministic.

## Acceptance criteria

- [ ] `ContentMaterializer` calls `llm_client` with a schema-bound request/response contract; `SlideDeckTraceMetadata.llm_calls` reflects real call counts, never a hardcoded literal.
- [ ] LLM output is parsed into typed blocks and re-validated by the existing registry/density/accessibility/teacher-only-leak validators before acceptance — no unvalidated LLM text reaches a slide.
- [ ] A live-path-proof test (per ADR-032) demonstrates the LLM call is reachable from the real teaching-pack graph, not just from a fixture that hand-constructs the phase's input.
- [ ] The ADR-044 real-LLM harness's 3 official scenarios (Grade5 ESL, Grade5 math/science, Vietnamese localization) exercise this call end-to-end and pass.
- [ ] Failure handling (LLM timeout/invalid schema) falls back to the engine's existing typed-healing mechanism (`density_overflow`, `invalid_layout_block`, etc.) rather than a silent placeholder.

## Blocked by

None — this closes an existing ADR-040 implementation gap and can start immediately.
