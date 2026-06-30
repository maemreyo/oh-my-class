---
title: Frontend unit workspace — dashboard, sequence editor, redirect
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Build the teacher-facing unit surface (ADR-017 §UI). A unit is a dashboard of parallel sessions, not a linear gate flow — so it gets its own route — while reusing the existing content-approval gate body for per-session review.

`apps/web`:

- Route `/units/[parentRunId]`: a dashboard of session cards (status, progress, current step), unit progress (`approved/total`), per-session actions (review / retry / spawn-anyway), `Approve all`, `Export unit`, and a `grounding_status` banner.
- `useUnit(unitId)` hook: hydrate via `GET /units/{id}` (react-query) + subscribe to `GET /units/{id}/status` (EventSource) with snapshot+cursor reconciliation matching issue 011.
- `UNIT_APPROVAL` gate body: a sequence editor — session list with title/objectives/Bloom/methodology/duration, prerequisite DAG visualization, reorder/add/remove/edit, theme preview; approve/reject/edit.
- Redirect: when a run's `unit_role` flips to `unit_parent` (event `run.became_unit`), redirect from the linear run view to `/units/{run_id}`. Contract confirmation still happens in the existing gate shell before redirect.
- Per-session content review reuses the existing `CONTENT_APPROVAL` gate body inside the dashboard.

Generated types come from `common/schemas` (issue 001) — no hand-written unit DTOs.

## Acceptance criteria

- [ ] `/units/[parentRunId]` renders session cards with live status, unit progress, and unit/per-session actions.
- [ ] `useUnit` hydrates from the read model and applies live deltas with cursor reconciliation; counts come from the backend, not derived client-side.
- [ ] The `UNIT_APPROVAL` body supports reorder/add/remove/edit and renders the prerequisite DAG and theme preview; reorder preserves `session_id` references.
- [ ] A run becoming a unit redirects to the workspace; contract confirmation precedes redirect in the linear shell.
- [ ] Per-session review reuses the `CONTENT_APPROVAL` body; no duplicate review UI.
- [ ] All unit types are imported from generated schemas; no hand-written transport interfaces.

## Detailed test suite

- [ ] `apps/web/tests/use-unit.test.ts` (vitest): hydrate + apply a `unit.session.status_changed` delta updates the right card; a stale (`cursor` ≤ snapshot) delta is ignored; reconnect re-snapshots.
- [ ] `apps/web/tests/unit-sequence-editor.test.tsx` (RTL): reordering sessions updates `order_index` while `session_id` prereq references are preserved; add/remove/edit validate.
- [ ] `apps/web/tests/unit-dashboard.test.tsx` (RTL): `Approve all` calls approve-all; `spawn-anyway` calls the unblock endpoint; a blocked card shows the override affordance.
- [ ] `pnpm -F web test:e2e` (Playwright) at 375/768/1280/1920: the dashboard and sequence editor render and are responsive; the content-approval body opens for a session.
- [ ] Redirect test: a run transitioning to `unit_parent` navigates to `/units/{id}`.
- [ ] Run `pnpm -F web test` and `pnpm -F web test:e2e`.

## Blocked by

- .scratch/topic-decomposition/011-unit-read-api-and-streaming.md
