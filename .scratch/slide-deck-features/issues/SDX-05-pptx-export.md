---
title: PPTX export (no PPTX import)
status: ready-for-agent
labels: [ready-for-agent, slide-deck, feature, export]
created: 2026-07-07
---

## Parent

ADR-042: Slide Deck Surfaces, Quality, and Release Gates (revisits the "PDF/PPTX deferred past v1" note for export only)

## What to build

Add `pptx` as a new export format via the existing `ExporterRegistry` pattern (alongside `html`, `gift`, `h5p`, `qti`), converting `SlideDeckData` to a `.pptx` file for offline/institutional use. PPTX **import** (converting an arbitrary existing PowerPoint into `SlideDeckData`) remains explicitly out of scope — it is a much harder reverse-mapping problem with no confirmed migration need yet.

## Acceptance criteria

- [ ] `ExportFormat` gains a `pptx` value; `ExporterRegistry` supports it fail-closed (like other formats — unsupported combinations error clearly, no silent degrade).
- [ ] Exported `.pptx` preserves slide layout/blocks/media in a visually reasonable approximation (exact ADR-041 layout fidelity is not required, since PowerPoint's layout model differs).
- [ ] Manifest `export_formats.supported` reflects `pptx` machine-verifiably, consistent with how other formats are tracked.
- [ ] No PPTX import/parsing code is added in this issue.

## Blocked by

- SDE-02-slide-capability-registry-full-contract.md
