---
title: AI-generated alt-text for AI-authored and teacher-uploaded media
status: ready-for-agent
labels: [ready-for-agent, slide-deck, feature, accessibility, llm]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision; `trust-lifecycle/001` (WCAG 2.1 AA)

## What to build

`SlideDeckMedia.alt_text` is already a required, non-empty schema field, but is currently template-generated (generic, not descriptive). Cover both sources of images: (1) AI-authored media generated during `ContentMaterializer` (SDE-01) gets a real descriptive alt-text in the same LLM call, at no extra cost; (2) teacher-uploaded images (via SDX-02's asset library) get a per-image "Generate alt text with AI" action in the editor, reusing SDE-08's AI-rewrite confirmation pattern.

## Acceptance criteria

- [ ] `ContentMaterializer`'s LLM call (SDE-01) produces a genuinely descriptive `alt_text` for any media block it authors, not a generic placeholder.
- [ ] The editor exposes a per-image "Tạo alt-text bằng AI" action for teacher-uploaded images (SDX-02), using the same before/after confirmation modal component as SDE-08.
- [ ] Generated alt text always satisfies the existing schema constraint (`min_length=1, max_length=500`).
- [ ] A guard test verifies no media block in a generated deck has empty or obviously-placeholder alt text (e.g. "image", "hình ảnh minh họa" alone).

## Blocked by

- SDE-01-content-materialization-llm-integration.md
- SDX-02-teacher-scoped-media-asset-library.md
