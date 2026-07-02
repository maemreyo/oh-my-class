---
title: CSS loader memoization for batch export performance
status: ready-for-agent
labels: [renderer, performance, loader]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## Why this issue exists

Issue 002's `loadArtifactCSS(familyId)` concatenates 4 CSS files per call. This is correct for
single renders. But vocabulary batch exports render 100+ clusters × 4 projections each = 400+
calls to `renderArtifactUi()`. Without memoization, a 100-cluster export reads 1,600 CSS files
from disk — all redundant, since the CSS is static per family.

The fix is a module-level Map cache. CSS files are static assets; they do not change between
renders in a single process. First call reads from disk; subsequent calls return the cached string.

## What to build

Update `packages/renderer/src/artifact-ui/loader.ts`:

```typescript
const cssCache = new Map<string, string>();

export function loadArtifactCSS(familyId: string): string {
  const cached = cssCache.get(familyId);
  if (cached !== undefined) return cached;

  const family = getFamily(familyId); // throws descriptive error if unknown
  const css = [
    readCSSFile("tokens/contract.css"),
    readCSSFile(`tokens/${family.id}.css`),
    readCSSFile("primitives.css"),
    readCSSFile(`families/${family.id}.css`),
  ].join("\n\n");

  cssCache.set(familyId, css);
  return css;
}

/** Clear the CSS cache — for testing only. */
export function clearArtifactCSSCache(): void {
  cssCache.clear();
}
```

The `clearArtifactCSSCache()` export is needed so tests that modify CSS files (or test
cache misses) can reset state between test cases without module re-loading.

## Acceptance criteria

- [ ] `loadArtifactCSS` uses a module-level `Map<string, string>` cache
- [ ] Second call to `loadArtifactCSS('navy-ticket')` returns cached string (no file reads)
- [ ] `clearArtifactCSSCache()` is exported and empties the cache
- [ ] Cache hit is transparent: returned string is byte-identical to uncached call
- [ ] Unknown family ID still throws descriptive error (cache does not mask it)
- [ ] Cache is keyed by `familyId` string — `loadArtifactCSS('navy-ticket')` and
      `loadArtifactCSS('paper-dossier')` are independent cache entries
- [ ] `pnpm --filter @oh-my-class/renderer typecheck` → no type errors

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/loader.test.ts`:
  - `loadArtifactCSS('navy-ticket')` called twice returns same reference (or identical string)
  - `clearArtifactCSSCache()` forces re-read on next call (spy on `fs.readFileSync`)
  - `loadArtifactCSS('nonexistent')` throws even after cache has other entries
  - `loadArtifactCSS('navy-ticket')` and `loadArtifactCSS('paper-dossier')` return different strings
  - Batch: 400 calls for 4 families → only 4 unique CSS strings in cache (16 file reads, not 1600)

## Verification

- `pnpm --filter @oh-my-class/renderer test -- --testPathPattern=artifact-ui/loader` → all pass
- Manual: add `console.count('css-read')` to `readCSSFile`, run vocabulary batch export with
  100 mock clusters → counter shows 4 total reads (not 400)

## Blocked by

- `002-family-registry-and-css-loader.md` — loader must exist before memoization can be added

## Design notes

### Why module-level, not function-level closure?

Module-level cache persists for the lifetime of the Node.js process. For long-running export
workers or server-side rendering, this is the right scope. CSS files are build-time artifacts;
they do not change while the process is running.

### Why not LRU or size-bounded?

There are exactly 4 families and 4 CSS strings, each ≤ 5 KB. Total max cache size ≈ 20 KB.
An unbounded Map is correct and simpler than LRU for this scale.

### Why not cache at the file-read level?

Caching at `familyId` level avoids reading 4 individual files for every cache miss on a new
family — and avoids building a per-file cache that exposes internal file paths as public API.
The family is the cache key because that's what callers reason about.
