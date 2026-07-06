# ADR-042: Slide Deck Surfaces, Quality Gates, and Release Evidence

## Status

**Proposed** (2026-07-06) — Defines the output surfaces, teacher UX, quality gates, export scope, and evidence required before native `slide_deck` can ship.

## Context

A slide deck has multiple audiences and usage modes. Students need a clean presentation surface. Teachers need facilitation notes, pacing, misconceptions, and answer guidance. Export needs print/PDF-friendly output. The existing system already enforces standalone HTML, teacher approval, compliance hard blocks, and artifact exports. `slide_deck` must fit those surfaces without creating a parallel approval or quality pipeline.

The main safety risks are answer-key leakage, teacher-only note leakage, unreadable dense slides, broken keyboard/reveal behavior, inaccessible interactions, external media in offline exports, and visual regressions that ordinary schema tests cannot catch.

## Decision

1. **One canonical `SlideDeckData`, three renderer surfaces.** The renderer produces:
   - Presentation HTML: student-facing, fullscreen/keyboard/reveal-capable, no teacher-only content.
   - Teacher guide/preview HTML: slide preview plus speaker notes, facilitation cues, pacing, misconceptions, and teacher-only answers.
   - Print HTML: page-break-friendly, offline, all-visible or step-expanded, suitable for browser print/PDF.
2. **Reuse the artifact lifecycle.** `slide_deck` appears in artifact progress, workflow status, quality results, teacher approval, scoped regeneration, and export finalize like other artifacts. It gets custom preview UX, but not a separate workflow.
3. **Teacher preview is slide-native.** The dashboard should present slide navigation, optional thumbnail/outline, teacher notes panel, student/teacher/print surface toggles, online-media warnings, and scoped reject/edit feedback targets.
4. **Scoped regeneration is required.** Slides, blocks, interactions, and deck-level plan objects carry stable IDs. Teacher feedback can target deck, slide, block, or interaction. The engine repairs the narrowest safe scope and falls back to full deck regeneration only when needed.
5. **The existing 6-layer quality system remains authoritative.** `slide_deck` adds validators to the current layers instead of creating a parallel quality pipeline.
6. **Layer-specific slide gates are required.**
   - Layer 1: `SlideDeckData`, layout/block/interaction unions, stable IDs, source refs, and teacher-only flags validate.
   - Layer 2: objective coverage, age appropriateness, factual grounding, pedagogical flow, and source refs validate.
   - Layer 3: standalone HTML, no default external assets, no teacher-only leak, keyboard navigation, print surface, and managed inline script policy validate.
   - Layer 4: judge rubric checks flow, visual clarity, classroom usability, interaction fit, and facilitation usefulness.
   - Layer 5: teacher approval uses slide-native preview and scoped feedback.
   - Layer 6: export readiness checks required surfaces and manifests.
7. **Deterministic scorecard precedes LLM judge.** The engine computes objective coverage, pacing fit, density, visual variety, accessibility completeness, interaction appropriateness, teacher-only separation, and offline readiness before Layer 4.
8. **Export scope starts with HTML surfaces.** Phase 1 produces standalone presentation, teacher, and print HTML. Native PDF and PPTX are future exporters and must not block the first production release.
9. **Visual/browser QA is mandatory for release evidence.** Unit and contract tests are not enough. A golden slide deck must be rendered through browser smoke at representative viewports, with navigation, reveal, focus, overflow, dark mode, and print behavior exercised.
10. **No answer data in student DOM.** Student-facing HTML must not include answer keys, correct answers, explanation data, teacher notes, hidden JSON answer payloads, or scrapeable teacher-only fields. Compliance must fail closed.

## Consequences

- Teachers get a slide-centric review experience while the system keeps one artifact lifecycle.
- Student safety and answer-key separation are enforceable because surfaces are projections from canonical data, not mode flags over one leaking HTML blob.
- The first production release focuses on reliable HTML outputs; richer PDF/PPTX export can be added later behind the same canonical model.
- Release requires browser-level QA and a golden fixture, increasing initial test investment but reducing UI regressions.
- Scoped regeneration becomes feasible because stable IDs and source refs are part of the model from the beginning.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Three surfaces from one canonical model (chosen) | Safe projection, teacher-friendly, testable | More renderer adapters and QA fixtures |
| Single HTML with mode query flags | Fewer files | High leakage risk; harder compliance and tests |
| Treat slide deck as ordinary long HTML preview | Cheap UI | Poor teacher UX; does not test navigation/presentation behavior |
| Add PDF/PPTX in first release | Attractive export story | Requires browser/image/font fidelity pipeline and much higher QA burden |
| Trust LLM judge for visual quality | Simple | Misses deterministic density, accessibility, and leak issues |

## References

- ADR-025 Renderer Artifact-Kind Plugin Registry Rewrite
- ADR-026 Fast-Lane Teacher Gate and Invariant-06
- ADR-031 Full Output Test Matrix
- ADR-040 Native Slide Deck Artifact and SlideDeckEngine
- ADR-041 Slide Deck Registries and Interaction Modules
- `packages/quality/compliance_policy.py`
- `services/gateway/teaching_pack_export_writer.py`
- `apps/web/src/components/teaching-packs-artifact-progress.tsx`
