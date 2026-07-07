---
title: Search/filter on the runs list page
status: ready-for-agent
labels: [ready-for-agent, frontend, app-ux]
created: 2026-07-07
---

## Parent

None — general app UX fix, not slide-deck-specific. Filed alongside the slide-deck feature set because growth in deck/asset/template volume (SDX-02, SDX-03) makes the gap acute sooner than expected.

## What to build

`apps/web/src/app/(dashboard)/runs/page.tsx` currently dumps every run into an unfiltered grid with no search/filter at all. Add basic filtering (title keyword, date, artifact type) directly to this existing page.

## Acceptance criteria

- [ ] A text input filters the existing run list by title keyword (client-side is acceptable at current expected volume; revisit server-side filtering if the list grows large).
- [ ] A date-range and/or artifact-type filter is available alongside the keyword search.
- [ ] The existing `RunCard`/`useRuns` components are reused unchanged — this is a filter layer added to the existing page, not a new page or new data-fetching hook.
- [ ] Empty-filter-result state is handled distinctly from the existing "no runs yet" empty state.

## Blocked by

None — can start immediately.
