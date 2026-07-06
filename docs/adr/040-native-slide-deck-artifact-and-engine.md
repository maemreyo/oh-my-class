# ADR-040: Native Slide Deck Artifact and SlideDeckEngine

## Status

**Proposed** (2026-07-06) — Adds `slide_deck` as a native teaching-pack artifact and defines `SlideDeckEngine` as the production generation module. This ADR intentionally rejects an `open-slide` runtime dependency; open-slide remains a design reference only.

## Context

Teachers need presentation-ready classroom slides as part of the same teaching pack that already produces lessons, worksheets, quizzes, drills, recaps, flashcards, roadmaps, and answer keys. A research pass evaluated `1weiho/open-slide` and found that it is an agent-first React/Vite slide workspace and presentation runtime, not a JSON-to-HTML rendering library or FastAPI-callable export API. Integrating it as the core renderer would add a Node/Vite/browser build subsystem and conflict with the project's standalone HTML, fail-closed quality, and typed ArtifactContent pipeline.

The existing system already has the correct extension seams:

- `ArtifactContent` and `RunContract` in `common/contracts` are the canonical output contracts.
- The teaching-pack graph owns orchestration; content generation stays behind the Content Creator boundary.
- Artifact fan-out supports dependency waves and scoped regeneration.
- The renderer is moving toward artifact-kind plugins with explicit audience, render mode, sanitizer, and manifest behavior.
- Quality and compliance gates already own answer-key leakage, standalone HTML, teacher approval, and export readiness.

The product goal is production-ready slide generation, not a prompt patch or an external slide sidecar.

## Decision

1. **`slide_deck` is a core artifact type.** It is requestable through `RunContract.artifact_types`, generated as `ArtifactContent`, tracked in artifact workflow status, reviewed at the teacher gate, rendered, quality checked, and exported like other artifacts.
2. **No `open-slide` dependency in the production path.** The implementation may borrow open-slide's useful ideas — a 16:9 presentation canvas, agent-friendly slide vocabulary, presenter/notes separation, and static sharing — but not its React/Vite runtime, CLI, or workspace model.
3. **The canonical slide content shape is typed.** `SlideDeckData` lives in `common/contracts` and is the domain model for decks, slides, blocks, interactions, teacher-only facilitation, source references, accessibility metadata, density budgets, and regeneration targets. Generated TypeScript/Zod schemas follow the existing schema generation path.
4. **`SlideDeckEngine` is a deep module behind the Content Creator seam.** Callers provide one typed request and receive one typed result. Internally the engine may use ports and registries, but graph nodes and downstream callers do not learn those internals.
5. **The engine is deterministic orchestration with schema-bound LLM steps.** LLM calls may propose slide plans and materialize content, but every LLM output is parsed into typed contracts and passed through deterministic policy, registry, density, accessibility, source-reference, and teacher-only validators.
6. **Engine phases are explicit and testable.** The initial production shape is:
   - `InputAssembler`
   - `PedagogicalPlanner`
   - `SlideArchitecturePlanner`
   - `LayoutComposer`
   - `InteractionPlanner`
   - `ContentMaterializer`
   - `DensityAndAccessibilityAuditor`
   - `SurfaceRenderer`
   - `ExportPackager`
7. **Page count and pacing are policy-driven.** Teacher overrides are supported, but unbounded page counts are not. Duration, grade band, objective count, delivery context, text density, interaction load, and export target inform the policy.
8. **Dependency handling is reference-based.** The engine consumes `DeckSourceContext` built from lesson blueprint, research brief, and approved dependency artifacts. Slide pages/blocks record `source_refs`; the engine does not copy whole worksheets/quizzes into slides or leak answer data.
9. **Healing is typed and scoped.** Engine validators produce typed failures such as `density_overflow`, `invalid_layout_block`, `teacher_only_leak`, `missing_alt_text`, `unsupported_interaction`, and `pacing_mismatch`. Repairs happen at block, slide, plan, or deck scope before escalating.
10. **Observability is first-class.** Each run can emit internal plan, data, validation reports, healing attempts, deterministic scorecard, render manifest, export manifest, model/cost metadata, and teacher feedback target maps. Student-facing output never contains internal traces, answer keys, PII, or teacher-only notes.

## Consequences

- `slide_deck` becomes a normal artifact in the authoritative stage graph rather than a parallel slide subsystem.
- Production determinism improves because layout, interaction, density, accessibility, and export behavior are validated by code, not left to an LLM prompt.
- The first implementation is larger than an external sidecar because contracts, engine interfaces, renderer surfaces, gates, and tests must land together in vertical slices.
- Future slide capability growth happens by adding registries/modules, not by widening a giant prompt or template switch.
- If a future native PPTX or browser-export service is needed, it must attach as an exporter to `SlideDeckData`, not replace the canonical artifact model.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Native `slide_deck` + `SlideDeckEngine` (chosen) | Preserves existing contracts, gates, standalone HTML, and graph lifecycle; testable and modular | Requires new contracts, engine, renderer, gates, and UI slices |
| Use open-slide as renderer/exporter | Rich present mode and agent-native authoring | Adds React/Vite/browser subsystem; no clean server API; conflicts with standalone/fail-closed requirements |
| Treat slides as export format derived from `lesson` | Smallest contract change | No independent artifact lifecycle, teacher approval, scoped regeneration, or slide-specific quality gates |
| Let Content Creator emit arbitrary HTML slides | Fast prototype | Violates typed contracts, sanitizer predictability, testability, and answer-leak controls |
| Build only static print slides | Lower interaction complexity | Misses teacher presentation and facilitation use cases |

## References

- ADR-020 LangGraph Send Artifact Fan-Out
- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-030 Full Artifact-Type and Export Coverage
- ADR-031 Full Output Test Matrix
- ADR-039 Component Strategy Blueprint and Delivery Semantics
- `common/contracts/artifact.py`
- `common/contracts/run_contract.py`
- `packages/agents/teaching_pack/artifact_fanout.py`
- `packages/agents/sub_agents/content_creator/`
