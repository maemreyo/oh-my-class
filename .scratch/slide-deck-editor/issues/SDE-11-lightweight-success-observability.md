---
title: Lightweight success observability (no new dashboard)
status: ready-for-agent
labels: [ready-for-agent, slide-deck, editor, observability]
created: 2026-07-07
---

## Parent

ADR-047: Slide Deck Editor and AI-Assisted Revision (decision 15)

## What to build

Emit a short list of concrete, queryable observability events through the existing `ObservabilityEventType` pipeline (per ADR-032's "every literal has a live emitter" rule) so the editor's value can be assessed honestly after launch — without building a new dashboard.

## Acceptance criteria

- [ ] Events are emitted for: deck edited within 24h of generation, AI-rewrite suggestion shown, AI-rewrite accepted vs. cancelled (from the SDE-08 confirmation modal), and teacher return-usage of the editor.
- [ ] Every new `ObservabilityEventType` literal added has a live emitter reachable from the real editor code paths — no defined-but-unemitted signals (the exact anti-pattern ADR-032's meta-test checks for).
- [ ] No new dashboard/UI is built to visualize these events in this slice — they are queried directly (e.g. via Langfuse/existing event store) for a manual review 4-6 weeks post-launch.
- [ ] Events never carry student PII (they are teacher/deck/session-scoped counts and timestamps only).

## Blocked by

- SDE-04-edit-api-versioning-and-concurrency.md
- SDE-08-ai-assisted-block-rewrite.md
