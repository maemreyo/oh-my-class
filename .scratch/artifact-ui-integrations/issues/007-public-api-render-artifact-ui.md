---
title: Public API — renderArtifactUi() entry point
status: ready-for-agent
labels: [renderer, api, public-interface]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Create the public `renderArtifactUi()` function that orchestrates the full Artifact UI render pipeline: CSS loading → contract adaptation → Eta template rendering → sanitization. This is the single entry point for all Artifact UI rendering.

## Acceptance criteria

- [ ] `src/artifact-ui/index.ts` exports `renderArtifactUi(request: ArtifactUiRenderRequest): Promise<string>`
- [ ] `ArtifactUiRenderRequest` type includes: family, contract, audience, kind, artifactType
- [ ] `renderArtifactUi` validates family ID against registry (throws descriptive error for unknown family)
- [ ] `renderArtifactUi` loads CSS via `loadArtifactCSS(family)`
- [ ] `renderArtifactUi` runs contract adapter to produce template data
- [ ] `renderArtifactUi` renders Eta template with CSS + adapted data
- [ ] `renderArtifactUi` sanitizes output via existing `sanitize(html, artifactType)`
- [ ] `renderArtifactUi` returns standalone HTML string
- [ ] Error handling: unknown family → descriptive error; missing contract fields → validation error; template not found → descriptive error
- [ ] Function is async (Eta renderAsync is async)
- [ ] No side effects (pure function given same inputs)

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders navy-ticket teaching teacher → HTML string with `data-artifact-theme="navy-ticket"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders paper-dossier lesson → HTML string with `data-artifact-theme="paper-dossier"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders transit-route video-route → HTML string with `data-artifact-theme="transit-route"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders investigation-folder inverse-thinking → HTML string with `data-artifact-theme="investigation-folder"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: unknown family throws descriptive error
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output is valid HTML5 (DOCTYPE, html, head, body)
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output contains no external URLs
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output contains `oh-my-class` brand string

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui` → all tests pass
- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: import `renderArtifactUi` in a test file, call with mock data, save output to `/tmp/test.html`, open in browser

## Blocked by

- `002-family-registry-and-css-loader.md` — loader must exist
- `003-eta-templates-all-families.md` — templates must exist
- `004-contract-adapters-all-families.md` — adapters must exist
