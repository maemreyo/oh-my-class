---
title: Teacher-scoped, minimal media asset library
status: ready-for-agent
labels: [ready-for-agent, slide-deck, feature]
created: 2026-07-07
---

## Parent

Future `trust-lifecycle/003` (Teacher content lifecycle — library + fork/re-edit); interim scope owned by ADR-047's editor track

## What to build

A minimal, teacher-scoped store for images/diagrams (with basic tagging) that can be reused across the teacher's own decks, so they don't need to re-upload the same asset per deck. Deliberately built in the same shape `trust-lifecycle/003`'s future general content library will need, so that epic can absorb this later rather than rebuilding it — but does not wait for that epic (`Status: TODO`, no ETA) to ship.

## Acceptance criteria

- [ ] A teacher can upload an image/diagram once and select it from a library when editing any deck they own (SDE-03).
- [ ] Assets are scoped to the owning teacher (reuses `check_run_owner`-equivalent ownership, no cross-teacher visibility in this slice).
- [ ] Basic tagging/filename search is supported; no full-text/AI-powered search is required in v1.
- [ ] Storage/ownership model matches whatever `trust-lifecycle/003` is expected to need (flat teacher-scoped object storage keys, not run-scoped) so future consolidation is additive, not a rewrite.
- [ ] Uploaded assets integrate with SDX-04 (alt-text generation) for images that arrive without AI-authored alt text.

## Blocked by

- SDE-03-structured-visual-block-editor.md
