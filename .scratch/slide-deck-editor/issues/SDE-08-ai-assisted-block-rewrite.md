---
title: AI-assisted, block-scoped rewrite with teacher confirmation
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, llm]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 4)

## What to build

Add a teacher-facing "rewrite this block" action: teacher picks a preset ("shorter," "add an example," "simplify language"...) or an optional freeform instruction; the same `ContentMaterializer` LLM step (SDE-01) regenerates just that block; a generic before/after confirmation modal (one component, reused for every block type) gates the result before it enters the draft. Never touches layout/architecture phases, and never scopes beyond one block in v1 (this is a deliberate boundary — see ADR-047 decision 4 — except the deck-level translation case in SDX-01).

## Acceptance criteria

- [ ] Preset instructions map to fixed prompt templates; an optional freeform text field is also available, routed through the identical validation pipeline as presets (no separate, less-validated path).
- [ ] Rewrite output is scoped to exactly one block; the action never modifies layout, slide structure, or any other block.
- [ ] A single generic before/after modal component (not one component per block type) shows the proposed change and requires an explicit "Apply"/"Cancel" before the result enters the local draft (SDE-07) — never auto-applied.
- [ ] Applied AI rewrites are tagged `authority: "ai_assisted_edit"` in the resulting `content_version.created` event (SDE-04), distinct from manual `"teacher_edit"`.
- [ ] Rejected ("Cancel") suggestions leave the draft completely unchanged.

## Blocked by

- SDE-01-content-materialization-llm-integration.md
- SDE-07-editor-frontend-route-and-draft-save.md
