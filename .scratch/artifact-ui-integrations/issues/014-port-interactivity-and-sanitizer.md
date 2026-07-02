---
title: Port interactivity.js + Artifact UI sanitizer layer
status: ready-for-agent
labels: [renderer, security, interactivity, sanitizer]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## Why this issue exists

Issue 001 ports 10 CSS files. Issue 007's `renderArtifactUi()` calls both a template renderer and
a sanitizer — but two pieces were missing: (a) the `interactivity.js` file was never scheduled
for porting into `packages/renderer/`, and (b) the existing `sanitize(html, type: ArtifactType)`
function is typed against the closed `ArtifactDataMap` union and cannot accept new Artifact UI
types without polluting the contract registry. This issue closes both gaps.

## What to build

### Part A — Port interactivity.js

Copy `resources/artifact-ui/interactivity.js` verbatim to
`packages/renderer/src/artifact-ui/interactivity.js`.

This file is vanilla JS (no eval, no remote src, 310 lines). It is loaded at render time by
`renderArtifactUi()` and injected into the `<head>` of templates that require reveal/toggle/jump
contracts (answer-key, root-cause-session).

**Placement in `<head>` is mandatory** — the existing `sanitize()` implementation only
sanitizes `<body>` content, leaving `<head>` (where inlined `<style>` and `<script>` live)
entirely untouched. Putting the script in `<head>` means it is never processed by
sanitize-html, which cannot safely allowlist inline script content.

### Part B — Artifact UI sanitizer config

Create `packages/renderer/src/sanitizer/configs/artifact-ui.ts`:

```typescript
import type { IOptions } from "sanitize-html";
import { BASE_CONFIG } from "../base-config.js";

/**
 * Sanitizer config for Artifact UI body content.
 *
 * Extends BASE_CONFIG with:
 * - Interactive elements: <button>, <details>, <summary>, <input type="hidden">
 * - SVG primitives for data visualizations (anchor-timeline, controlled-comparison)
 * - <a> with internal anchor hrefs only (#fragment — jump-to-target contract)
 *
 * <style> and <script> blocks live in <head> and are never passed to this config.
 * The existing sanitize() body-extraction pattern handles that invariant.
 */
export const ARTIFACT_UI_CONFIG: IOptions = {
  ...BASE_CONFIG,
  allowedTags: [
    ...(BASE_CONFIG.allowedTags as string[]),
    "button", "details", "summary",
    // SVG for data-viz primitives
    "svg", "g", "path", "circle", "rect", "line", "text", "tspan",
    "defs", "linearGradient", "stop",
  ],
  allowedAttributes: {
    ...BASE_CONFIG.allowedAttributes,
    "button": ["type", "data-toggle-reveal", "data-hide-after-reveal",
               "data-collapsed-label", "data-expanded-label",
               "data-toggle-group", "data-mode-toggle", "data-toggles-group",
               "data-jump-go", "aria-expanded", "aria-controls", "aria-checked"],
    "input":  ["type", "data-jump-input-el", "data-jump-to", "placeholder"],
    "a":      ["href"],   // href validated by exclusiveFilter (only #fragments allowed)
    "svg":    ["viewBox", "xmlns", "width", "height", "aria-hidden", "role"],
    "path":   ["d", "stroke", "fill", "stroke-width", "stroke-linecap"],
    "circle": ["cx", "cy", "r", "fill", "stroke"],
    "rect":   ["x", "y", "width", "height", "rx", "fill"],
    "line":   ["x1", "y1", "x2", "y2", "stroke", "stroke-width"],
    "text":   ["x", "y", "text-anchor", "dominant-baseline", "font-size", "fill"],
    "tspan":  ["x", "dy"],
    "stop":   ["offset", "stop-color", "stop-opacity"],
    "linearGradient": ["id", "x1", "y1", "x2", "y2"],
  },
  exclusiveFilter: (frame) => {
    // Block all http/https src references (from BASE_CONFIG)
    if (frame.attribs.src && !frame.attribs.src.startsWith("data:")) return true;
    // Allow only #fragment hrefs (jump-to-target contract), block all external URLs
    if (frame.attribs.href && !/^#/.test(frame.attribs.href)) return true;
    return false;
  },
};
```

### Part C — `sanitizeArtifactUi()` export

Add to `packages/renderer/src/sanitizer/index.ts`:

```typescript
import { ARTIFACT_UI_CONFIG } from "./configs/artifact-ui.js";

/**
 * Sanitize Artifact UI HTML output.
 *
 * Unlike sanitize(), this function is NOT typed against ArtifactType because
 * Artifact UI types (navy-ticket, paper-dossier, etc.) are render-layer concepts,
 * not schema-layer types. They must not pollute ArtifactDataMap.
 *
 * Sanitizes <body> content only. <head> content (inlined CSS + interactivity.js)
 * is trusted renderer output and is never passed to sanitize-html.
 */
export function sanitizeArtifactUi(html: string): string {
  const bodyMatch = html.match(/(<body[^>]*>)([\s\S]*)(<\/body>)/i);
  if (bodyMatch) {
    const sanitizedBody = sanitizeHtmlLib(bodyMatch[2], ARTIFACT_UI_CONFIG);
    return html.replace(bodyMatch[0], `${bodyMatch[1]}${sanitizedBody}${bodyMatch[3]}`);
  }
  return sanitizeHtmlLib(html, ARTIFACT_UI_CONFIG);
}
```

## Acceptance criteria

- [ ] `src/artifact-ui/interactivity.js` exists, byte-identical to `resources/artifact-ui/interactivity.js`
- [ ] `interactivity.js` contains zero `eval(` occurrences
- [ ] `interactivity.js` contains zero `http://` or `https://` references
- [ ] `sanitizer/configs/artifact-ui.ts` exports `ARTIFACT_UI_CONFIG`
- [ ] `ARTIFACT_UI_CONFIG` extends `BASE_CONFIG` (no independent allowlists)
- [ ] `ARTIFACT_UI_CONFIG` allows SVG primitives needed for data-viz components
- [ ] `ARTIFACT_UI_CONFIG` allows all `data-*` attributes (inherited from BASE_CONFIG)
- [ ] `ARTIFACT_UI_CONFIG` `exclusiveFilter` allows only `#fragment` hrefs (jump-to-target)
- [ ] `ARTIFACT_UI_CONFIG` `exclusiveFilter` blocks all `http://`/`https://` hrefs
- [ ] `sanitizer/index.ts` exports `sanitizeArtifactUi(html: string): string`
- [ ] `sanitizeArtifactUi` only sanitizes `<body>` content (identical body-extraction pattern)
- [ ] `ArtifactDataMap` is NOT modified (no new artifact types added to schema registry)
- [ ] `pnpm --filter @oh-my-class/renderer typecheck` → no type errors

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/interactivity-js.test.ts`:
  - File exists at `src/artifact-ui/interactivity.js`
  - Content contains zero `eval(`
  - Content contains zero `http://`
  - Content is non-empty (≥ 100 characters)
- [ ] `packages/renderer/__tests__/artifact-ui/sanitizer.test.ts`:
  - `sanitizeArtifactUi` preserves `data-toggle-reveal` attribute
  - `sanitizeArtifactUi` preserves `aria-expanded` attribute
  - `sanitizeArtifactUi` preserves `art-*` CSS classes
  - `sanitizeArtifactUi` strips `href="https://evil.com"` (returns no href)
  - `sanitizeArtifactUi` preserves `href="#question-3"` (internal jump)
  - `sanitizeArtifactUi` strips `<script>` from `<body>` content (body scripts are untrusted)
  - `sanitizeArtifactUi` preserves `<button data-toggle-reveal="answer-1">` element
  - `sanitizeArtifactUi` preserves `<svg>` with `<path>` children
  - `sanitizeArtifactUi` on full document only touches body (head preserved verbatim)
  - `ARTIFACT_UI_CONFIG` is a proper superset of `BASE_CONFIG` (all BASE_CONFIG tags present)

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui/sanitizer` → all pass
- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui/interactivity-js` → all pass
- Manual: `grep -c "eval(" src/artifact-ui/interactivity.js` → 0
- Manual: `grep -c "http" src/artifact-ui/interactivity.js` → 0

## Blocked by

None — can start immediately. `interactivity.js` is ready in resources.

## Design note: why NOT extend ArtifactDataMap

Adding `navy-ticket`, `video-route`, `investigation-folder` etc. to `ArtifactDataMap` and
`ArtifactType` would couple the render-layer concept of "visual family" to the schema-layer
concept of "artifact type." These are different axes:

- Artifact type = what the content IS (a lesson, a quiz, a vocab cluster)
- Visual family = how it LOOKS (navy-ticket, paper-dossier)

One artifact type (lesson) maps to one visual family (paper-dossier). But a second lesson-like
type (root-cause-session) also maps to paper-dossier. The mapping is N:1, not 1:1. Putting
families into `ArtifactDataMap` would either require inventing fake "lesson-paper-dossier" types
or duplicating adapter code. `sanitizeArtifactUi()` as a separate function keeps the two axes
clean.
