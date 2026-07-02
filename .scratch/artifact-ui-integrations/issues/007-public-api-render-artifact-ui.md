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

**Interactivity support:** The API must support inlining `interactivity.js` for templates that use reveal/toggle/jump contracts (answer-key, root-cause-session). The JS is loaded from `src/artifact-ui/interactivity.js` (ported by Issue 014) and passed to the Eta template as `interactivityJS` variable. Templates place the `<script>` block in `<head>`, not `<body>`, so it is never processed by the sanitizer.

**Sanitizer:** `renderArtifactUi` calls `sanitizeArtifactUi(html)` — NOT `sanitize(html, type: ArtifactType)`. See Issue 014 for the design rationale. `ArtifactDataMap` is not extended with Artifact UI family names.

**Audience:** `audience` is always set explicitly by the caller — never inferred from artifact content. There is no default. Callers that do not pass `audience` should get a TypeScript compile error.

## Acceptance criteria

- [ ] `src/artifact-ui/index.ts` exports `renderArtifactUi(request: ArtifactUiRenderRequest): Promise<string>`
- [ ] `ArtifactUiRenderRequest` type includes: family, contract, audience, kind, artifactType
- [ ] `renderArtifactUi` validates family ID against registry (throws descriptive error for unknown family)
- [ ] `renderArtifactUi` loads CSS via `loadArtifactCSS(family)`
- [ ] `renderArtifactUi` loads `interactivity.js` content when adapter sets `useInteractivity: true`
- [ ] `renderArtifactUi` passes `interactivityJS` to Eta template when present
- [ ] `renderArtifactUi` runs contract adapter to produce template data
- [ ] `renderArtifactUi` renders Eta template with CSS + adapted data + optional interactivityJS
- [ ] `renderArtifactUi` sanitizes output via `sanitizeArtifactUi(html)` (Issue 014, NOT the typed `sanitize(html, type: ArtifactType)`)
- [ ] `renderArtifactUi` returns standalone HTML string
- [ ] Error handling: unknown family → descriptive error; missing contract fields → validation error; template not found → descriptive error
- [ ] Function is async (Eta renderAsync is async)
- [ ] No side effects (pure function given same inputs)
- [ ] `interactivity.js` is loaded from `src/artifact-ui/interactivity.js` (not hardcoded)
- [ ] `ArtifactUiRenderRequest.audience` is required — TypeScript compiler rejects calls without it
- [ ] `src/artifact-ui/index.ts` also exports `renderArtifactUiSet(request: ArtifactUiSetRequest): Promise<ArtifactUiSet>` — convenience wrapper for navy-ticket batch projections (see below)

### `renderArtifactUiSet` spec

```typescript
export interface ArtifactUiSetRequest {
  cluster: SemanticAnchorCluster;
  practiceSet: PracticeSet;
  artifactType?: string;  // defaults to 'vocabulary_batch'
}

export interface ArtifactUiSet {
  teachingTeacher: string;
  teachingStudent: string;
  practiceTeacher: string;
  practiceStudent: string;
}

/**
 * Renders all 4 projections for a navy-ticket vocabulary cluster in parallel.
 * Replaces the old renderSemanticAnchorProjectionSet() shape exactly.
 */
export async function renderArtifactUiSet(request: ArtifactUiSetRequest): Promise<ArtifactUiSet> {
  const base = { family: 'navy-ticket' as const, contract: request.cluster };
  const [teachingTeacher, teachingStudent, practiceTeacher, practiceStudent] = await Promise.all([
    renderArtifactUi({ ...base, audience: 'teacher', kind: 'teaching' }),
    renderArtifactUi({ ...base, audience: 'student', kind: 'teaching' }),
    renderArtifactUi({ ...base, practiceSet: request.practiceSet, audience: 'teacher', kind: 'practice' }),
    renderArtifactUi({ ...base, practiceSet: request.practiceSet, audience: 'student', kind: 'practice' }),
  ]);
  return { teachingTeacher, teachingStudent, practiceTeacher, practiceStudent };
}
```

This mirrors `renderSemanticAnchorProjectionSet` in return shape so Issue 011's migration is a one-line import swap.

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders navy-ticket teaching teacher → HTML string with `data-artifact-theme="navy-ticket"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders paper-dossier lesson → HTML string with `data-artifact-theme="paper-dossier"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders transit-route video-route → HTML string with `data-artifact-theme="transit-route"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders investigation-folder inverse-thinking → HTML string with `data-artifact-theme="investigation-folder"`
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders paper-dossier answer-key → output contains `<script>` block with interactivity.js
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders paper-dossier root-cause-session → output contains `<script>` block with interactivity.js
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: renders paper-dossier lesson → output does NOT contain `<script>` block (no interactivity needed)
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: unknown family throws descriptive error
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output is valid HTML5 (DOCTYPE, html, head, body)
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output contains no external URLs
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: output contains `oh-my-class` brand string
- [ ] `packages/renderer/__tests__/artifact-ui/render-artifact-ui.test.ts`: interactivity.js inlined output contains no `eval(`

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui` → all tests pass
- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: import `renderArtifactUi` in a test file, call with mock data, save output to `/tmp/test.html`, open in browser

## Blocked by

- `002-family-registry-and-css-loader.md` — loader must exist
- `003-eta-templates-all-families.md` — templates must exist
- `004-contract-adapters-all-families.md` — adapters must exist
- `014-port-interactivity-and-sanitizer.md` — `sanitizeArtifactUi()` and `interactivity.js` must exist
