---
title: Family registry and CSS loader
status: ready-for-agent
labels: [renderer, typescript, architecture]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Create the family registry and CSS loader that make adding a new artifact UI family mechanical. The registry is a TypeScript file mapping family IDs to their CSS files, templates, and adapters. The loader reads CSS files and concatenates them in the correct order for inlining.

This slice establishes the extensibility pattern: adding a new family later means adding one registry entry + CSS files + templates + adapter. No changes to loader, renderer, or existing families.

## Acceptance criteria

- [ ] `src/artifact-ui/registry.ts` defines `ArtifactFamily` interface and `ARTIFACT_FAMILIES` array with all 4 families
- [ ] `ArtifactFamily` includes: id, name, tokenFile, familyFile, templateDir, adapterName, supportedTypes
- [ ] `ARTIFACT_FAMILIES` is `readonly` and contains entries for navy-ticket, paper-dossier, transit-route, investigation-folder
- [ ] `src/artifact-ui/loader.ts` exports `loadArtifactCSS(familyId: string): string`
- [ ] `loadArtifactCSS` concatenates: contract.css → family tokens → primitives.css → family components (in that order)
- [ ] `loadArtifactCSS` throws descriptive error for unknown family ID
- [ ] `src/artifact-ui/index.ts` re-exports `loadArtifactCSS`, `ARTIFACT_FAMILIES`, `ArtifactFamily`
- [ ] Registry uses `as const` for type safety (family IDs are string literals, not `string`)
- [ ] No CSS content is read at module load time (lazy loading via function call)

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/registry.test.ts`: `ARTIFACT_FAMILIES` contains exactly 4 entries with expected IDs
- [ ] `packages/renderer/__tests__/artifact-ui/registry.test.ts`: `getFamily('navy-ticket')` returns correct entry
- [ ] `packages/renderer/__tests__/artifact-ui/registry.test.ts`: `getFamily('nonexistent')` throws with descriptive message
- [ ] `packages/renderer/__tests__/artifact-ui/loader.test.ts`: `loadArtifactCSS('navy-ticket')` returns string containing `data-artifact-theme="navy-ticket"` selector
- [ ] `packages/renderer/__tests__/artifact-ui/loader.test.ts`: `loadArtifactCSS('navy-ticket')` output starts with contract.css content
- [ ] `packages/renderer/__tests__/artifact-ui/loader.test.ts`: `loadArtifactCSS` output contains no `http://` or `https://`
- [ ] `packages/renderer/__tests__/artifact-ui/loader.test.ts`: `loadArtifactCSS('nonexistent')` throws

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui` → all tests pass
- `pnpm --filter @oh-my-class/renderer typecheck` → no type errors
- Manual: import `loadArtifactCSS` in a test file, call it, verify output is a valid CSS string

## Blocked by

- `001-port-css-foundation.md` — CSS files must exist at the correct paths before the loader can read them
