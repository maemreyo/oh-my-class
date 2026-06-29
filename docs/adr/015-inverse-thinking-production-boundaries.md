# ADR-015: Inverse Thinking Production Boundaries

## Status

**Decided** (2026-06-30) — inverse thinking uses a clean v2 data path with adapters into existing artifacts and components.

## Context

oh-my-class already has methodology tags, Pydantic contracts, generated TypeScript/Zod schemas, a TypeScript renderer, Python quality gates, and a teacher dashboard. The inverse-thinking feature must fit these boundaries without overloading generic fields or putting pedagogy logic in the renderer.

The project values SoC, modularity, standalone HTML, fail-closed quality gates, and typed end-to-end contracts. A production implementation should be easy to test and evolve across lesson, worksheet, quiz, drill, and future export formats.

## Decision

Use a clean v2 path with adapters:

- `common/contracts` owns canonical Pydantic v2 models such as `InverseThinkingPack`, `InverseThinkingCase`, `CreativeFrameSelection`, and projection contracts.
- `common/schemas` receives generated TypeScript/Zod types from the Pydantic source of truth.
- `packages/methodologies` is introduced as a pure domain package. Its first module is `packages/methodologies/inverse_thinking`.
- `packages/methodologies/inverse_thinking` validates, normalizes, and projects one canonical pack into lesson, worksheet, quiz, and drill data.
- `packages/quality` consumes methodology validators and reports critical failures or repairable warnings.
- `packages/renderer` remains presentation-only. It renders projected components and never invents pedagogy.
- `apps/web` uses generated schemas for teacher controls, structured editing, preview, and inspector UI.
- `services/gateway` orchestrates feature flags, run state, and pipeline wiring; it does not own inverse-thinking domain logic.

Maintain compatibility with existing shapes:

- Existing `methodology_tags` keep working.
- Add `inverse_thinking` as a supported methodology tag for discovery and compatibility.
- Add structured methodology payload data, for example `methodology_payloads.inverse_thinking`, for production behavior.
- Keep `ContentComponent[]` as the renderer target.
- Projection adapters compile `InverseThinkingPack` into current/new component variants.

## Consequences

- The quality system can validate semantic fields instead of parsing rendered HTML or free prose.
- Existing lessons and artifacts are not broken.
- New inverse-thinking functionality does not become a renderer concern.
- The same canonical pack can drive consistent lesson, worksheet, quiz, and drill projections.
- Future `recap`, `infographic`, H5P, GIFT, and QTI support can be added as projection/export work instead of regenerating pedagogy.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Store all inverse data in generic components only | Reuses renderer target | Weak validation and poor authoring semantics |
| Put projection logic in renderer | Fewer packages | Violates SoC; renderer would own pedagogy |
| Put domain logic in gateway | Easy orchestration access | Couples runtime service to reusable methodology logic |
| Dedicated methodology package with adapters | Modular, testable, reusable | Requires package wiring and tests |
