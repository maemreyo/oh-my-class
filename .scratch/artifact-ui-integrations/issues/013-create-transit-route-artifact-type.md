---
title: Create transit-route video learning route artifact type
status: ready-for-agent
labels: [renderer, new-artifact, transit-route, video]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Create the transit-route video learning route artifact type. Unlike the other 3 families (which replace existing renderers), transit-route is a **new** artifact type with no existing renderer to replace. It needs:

1. A typed contract for video route data
2. A transit-route adapter
3. An Eta template
4. Registration in the artifact type system

This slice creates the video-route rendering capability that didn't exist before.

## Current state

- No `video-route` artifact type exists in `ArtifactDataMap`
- No `renderVideoRoute()` function exists
- No video route contract exists in `common/contracts/` or `packages/renderer/src/contracts/`
- The transit-route CSS family exists (tokens + components) but has no template to consume it

## Target state

- `VideoRouteData` contract in `packages/renderer/src/contracts/video-route.ts`
- `transitRouteAdapter` in `src/artifact-ui/adapters/transit-route.ts`
- `templates/artifact/transit-route/video-route.html` Eta template
- `renderArtifactUi({ family: 'transit-route', ... })` works end-to-end
- Registered in `ArtifactDataMap` and `ARTIFACT_FAMILIES`

## Acceptance criteria

- [ ] `VideoRouteData` contract exists with: title, subject, gradeLevel, stations[], videoMetadata, theme, lang
- [ ] `VideoRouteStation` type includes: code, title, description, duration, cues[]
- [ ] Transit-route adapter transforms `VideoRouteData` → template data shape
- [ ] Eta template renders: ticket header, mini route map, station cards, timeline steps, video placeholder
- [ ] Video placeholder is offline-safe (no `<video>` or `<iframe>` src — metadata only, per INVARIANT-04)
- [ ] `renderArtifactUi({ family: 'transit-route', ... })` produces valid standalone HTML
- [ ] Output contains `data-artifact-theme="transit-route"`
- [ ] Output uses `art-*` CSS classes (art-ticket-header, art-miniroute, art-station, etc.)
- [ ] Registered in `ArtifactDataMap` (or handled as a new type in `renderArtifactUi`)
- [ ] Registered in `ARTIFACT_FAMILIES` with `supportedTypes: ['video-route']`

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: renders video-route with mock data → valid HTML
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains `data-artifact-theme="transit-route"`
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains `art-ticket-header` class
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains `art-station` class
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains NO `<video` or `<iframe` tags
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains `oh-my-class` brand string
- [ ] `packages/renderer/__tests__/artifact-ui/transit-route.test.ts`: output contains no external URLs

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=transit-route` → all tests pass
- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: render a video-route with mock data, save to `/tmp/video-route.html`, open in browser
- Manual: verify ticket header, route map, station cards, timeline all render correctly

## Blocked by

- `002-family-registry-and-css-loader.md` — registry must exist
- `003-eta-templates-all-families.md` — transit-route template must exist
- `004-contract-adapters-all-families.md` — transit-route adapter must exist
- `007-public-api-render-artifact-ui.md` — renderArtifactUi() must exist
