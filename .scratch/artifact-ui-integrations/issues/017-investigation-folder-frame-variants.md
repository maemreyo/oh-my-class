---
title: Investigation folder — specify detective/neutral frame as template conditional
status: ready-for-agent
labels: [renderer, investigation-folder, inverse-thinking, templates]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## Why this issue exists

Issue 006 migrates `inverse-thinking-renderer.ts` to Artifact UI and states:
"Detective/neutral frame support moves to adapter or template variant."
It does not specify which. This ambiguity means an implementing agent will make an
arbitrary choice that may conflict with existing tests in
`packages/renderer/__tests__/inverse-thinking-frames.test.ts`.

This issue closes the design question with a concrete specification before Issue 006 is
implemented.

## Decision

**Single template, template-level conditional** — NOT separate template files.

`templates/artifact/investigation-folder/inverse-thinking.html` uses Eta conditionals
to apply the frame variant:

```eta
<% if (it.frameVariant === 'detective') { %>
  <div class="art-folder-cover art-folder-cover--detective">
<% } else { %>
  <div class="art-folder-cover art-folder-cover--neutral">
<% } %>
```

The adapter sets `frameVariant: 'detective' | 'neutral'` in its output data shape.
CSS classes `art-folder-cover--detective` and `art-folder-cover--neutral` handle
the visual distinction (color, header typography, icon treatment).

### Why not separate template files?

The frame variants share 95%+ of their markup. Two files would diverge silently over time.
A conditional in one file is the correct callsite for a single-axis presentation variant.

### Why not an adapter flag?

An adapter flag (e.g. `isDetective: boolean`) works, but a string literal union
(`'detective' | 'neutral'`) is more extensible if a third frame variant is introduced
and is clearer to read in template code. Both are fine; string literal is preferred.

## What to build

### 1. Update `adapters/investigation-folder.ts` output shape

Add `frameVariant: 'detective' | 'neutral'` to the adapter's output interface:

```typescript
export interface InvestigationFolderTemplateData {
  // ... existing fields
  frameVariant: 'detective' | 'neutral';
}
```

Map from `InverseThinkingRenderInput`:
- If the input has a `frame` field with value `'detective'` → `'detective'`
- Otherwise → `'neutral'` (safe default)

### 2. Update `templates/artifact/investigation-folder/inverse-thinking.html`

Use `it.frameVariant` for:
- `art-folder-cover` modifier class
- Cover header typography class (detective uses condensed uppercase, neutral uses regular)
- No other differences — the rest of the template is identical for both variants

### 3. Verify existing frame tests pass

`packages/renderer/__tests__/inverse-thinking-frames.test.ts` tests detective and neutral
frames using the old renderer. After Issue 006's migration, those tests must still pass
(same public API, new rendering path). This issue ensures the template supports both variants
so Issue 006's migration does not break them.

## Acceptance criteria

- [ ] `InvestigationFolderTemplateData` has `frameVariant: 'detective' | 'neutral'` field
- [ ] `investigation-folder` adapter maps `input.frame === 'detective'` → `'detective'`, else `'neutral'`
- [ ] `inverse-thinking.html` uses `it.frameVariant` for the cover modifier class
- [ ] `inverse-thinking.html` is a single template (not split into detective.html + neutral.html)
- [ ] Detective output contains `art-folder-cover--detective` class
- [ ] Neutral output contains `art-folder-cover--neutral` class
- [ ] Both variants pass standalone HTML invariants (DOCTYPE, brand string, no external URLs)

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/investigation-folder-frames.test.ts`:
  - `renderArtifactUi` with `frame: 'detective'` → output contains `art-folder-cover--detective`
  - `renderArtifactUi` with `frame: 'neutral'` → output contains `art-folder-cover--neutral`
  - `renderArtifactUi` with no `frame` field → output contains `art-folder-cover--neutral` (safe default)
  - Both variants produce valid standalone HTML

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=inverse-thinking-frames` → all pass (existing)
- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui/investigation-folder` → all pass (new)

## Blocked by

- `003-eta-templates-all-families.md` — template must exist
- `004-contract-adapters-all-families.md` — adapter interface must exist

## Note for Issue 006 implementing agent

Reference this issue's decision before implementing the detective/neutral frame in
`inverse-thinking-renderer.ts`'s migration. Specifically:
- The adapter reads `input.frame` (or `input.frameVariant`, check existing `InverseThinkingRenderInput` type)
- The output always sets `frameVariant` explicitly
- The template uses `it.frameVariant` as the CSS modifier key
