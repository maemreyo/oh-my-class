---
title: Generate and export a minimal slide_deck tracer through the teaching-pack pipeline
status: ready-for-agent
labels: [slide-deck-engine, pipeline, renderer, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-040, ADR-042.

## What to build

Deliver the first end-to-end native `slide_deck` tracer. A teacher request that includes `slide_deck` should produce a minimal valid deck, render it to standalone HTML, pass the existing quality/compliance path, appear as an artifact workflow status, and export an HTML file.

This is not the full slide experience. It is the narrow vertical slice proving that contracts, Content Creator integration, artifact fanout, renderer plugin/template, quality gates, snapshot/preview plumbing, and export writer can all carry one simple `slide_deck` artifact through the existing runtime.

The tracer deck can use a small set of layouts and blocks, but it must use the real `SlideDeckData` contract and must not use arbitrary HTML or open-slide.

## Acceptance criteria

- [ ] A run contract can request `slide_deck` without clarification or unsupported-artifact failure.
- [ ] Content Creator can return a valid `ArtifactContent` for `slide_deck` using `SlideDeckEngine` or its deterministic adapter.
- [ ] Artifact fanout schedules `slide_deck` after its required lesson dependency and records per-artifact workflow status.
- [ ] Renderer has a `slide_deck` artifact-kind plugin/template that emits standalone HTML with `DOCTYPE`, viewport meta, inline CSS, `oh-my-class` branding, and no external asset URLs.
- [ ] Render quality/compliance does not need a special bypass for `slide_deck`.
- [ ] Export finalize writes a `slide_deck` HTML artifact for approved snapshots.
- [ ] A focused integration test proves a minimal lesson + slide_deck run reaches exported HTML.

## Blocked by

- SD-01 slide deck contracts and schema parity.
- SD-02 SlideDeckEngine skeleton and typed registries.

## References

- `docs/adr/020-langgraph-send-artifact-fanout.md`
- `docs/adr/025-renderer-artifact-kind-plugin-registry.md`
- `docs/adr/040-native-slide-deck-artifact-and-engine.md`
- `packages/agents/teaching_pack/artifact_fanout.py`
- `packages/agents/teaching_pack/generate_one_artifact.py`
- `packages/renderer/src/core/runtime.ts`
- `packages/renderer/templates/pages/`
- `services/gateway/teaching_pack_export_writer.py`

## Implementation notes

- Keep this slice thin but real. Do not postpone renderer/export/quality integration to a later horizontal issue.
- If existing renderer registry migration work is incomplete, adapt to the current smallest production renderer seam while preserving ADR-025 direction.
- Do not add PDF/PPTX or online media in this slice.
