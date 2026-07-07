---
title: Dual-path edit API, snapshot versioning, and optimistic locking
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, backend]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decisions 5, 6, 9)

## What to build

Add a slide-scoped equivalent of `apply_scoped_section_edit()` (which cannot be reused as-is — it operates on a flat `sections` list, not `slides[].blocks[]`). Expose it through two entry points sharing this one business function: (1) the existing gate-resume `action: "edit"` flow, unchanged for teachers; (2) a new standalone endpoint, decoupled from graph/gate state, for revising any existing snapshot at any time (including post-approval/export).

## Acceptance criteria

- [ ] A single business function applies a scoped block edit to `SlideDeckData` and emits `content_version.created` with `authority: "teacher_edit"` (or `"ai_assisted_edit"` — see SDE-08), regardless of which endpoint called it.
- [ ] The gate-resume path continues to work exactly as `TeachingPackSectionEditor`'s existing flow does today, for slide decks.
- [ ] The new standalone endpoint accepts edits against any snapshot the requesting teacher owns, independent of the run's current graph/gate state.
- [ ] Every edit creates a new immutable snapshot version; the endpoint requires a `base_snapshot_id` and returns 409 Conflict if it doesn't match the current head (optimistic locking — no pessimistic locks, no silent last-write-wins).
- [ ] Authorization reuses `check_run_owner` (`services/gateway/auth/ownership.py`) unchanged — no new co-editor/shared-ownership model.
- [ ] A live-path-proof test confirms both entry points are reachable from the real gateway router, not only from a unit test that calls the business function directly.

## Blocked by

- SDE-03-structured-visual-block-editor.md
