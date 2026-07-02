---
title: Capture current renderer golden baselines before rewrite
status: completed
labels: []
created: 2026-07-02
completed: 2026-07-02
---

## Parent

ADR-025: Renderer Artifact-Kind Plugin Registry Rewrite

## What to build

Capture golden baselines from the current renderer before any rewrite work changes rendering behavior. This is the safety net for the big-bang outcome: the new plugin registry can be built in slices, but each migrated artifact kind must be compared against known current output instead of being rewritten blind.

The baselines should cover representative current outputs for regular artifacts, Artifact UI paths, subprocess rendering, and exporter-driven rendering where applicable.

## Acceptance criteria

- [x] Golden baseline harness renders representative current artifacts without using the new plugin registry.
- [x] Baselines cover at least quiz, worksheet, drill, recap, infographic, lesson, answer_key, semantic-anchor vocabulary projections, inverse-thinking, root-cause session, and video-route where current renderers exist.
- [x] Baselines include HTML snapshots and, for visual artifacts, DOM-stable visual fixtures suitable for later comparison.
- [x] Baseline capture records renderer/template/theme versions or source commit identity so future comparisons are meaningful.
- [x] Documentation explains how migrated plugins compare against the baseline and how intentional visual changes are approved.
- [x] The baseline harness is CI-runnable or clearly marked with an environment gate if browser screenshots are required.

## Implementation

- Added `packages/renderer/__tests__/current-renderer-baselines.test.ts`.
- Added current HTML baselines under `packages/renderer/__tests__/baselines/current-renderer/`.
- Added `metadata.json` with package identity, captured git commit, source files, baseline IDs, and the update command.

## Baseline workflow

Migrated plugins must render their output through the new path and compare it against the matching current-renderer baseline in `packages/renderer/__tests__/baselines/current-renderer/`.

If a visual or markup change is intentional, update the baseline with:

```bash
UPDATE_CURRENT_RENDERER_BASELINES=1 pnpm --filter @oh-my-class/renderer exec vitest run __tests__/current-renderer-baselines.test.ts
```

The review must include why the difference is intentional and which artifact kind changed. Unexplained baseline diffs are regressions.

## Verification

- `UPDATE_CURRENT_RENDERER_BASELINES=1 pnpm --filter @oh-my-class/renderer exec vitest run __tests__/current-renderer-baselines.test.ts` passed and generated the baseline files.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/current-renderer-baselines.test.ts` passed without update mode.
- `pnpm --filter @oh-my-class/renderer exec vitest run __tests__/current-renderer-baselines.test.ts __tests__/artifact-ui/render-artifact-ui.test.ts __tests__/agent-renderer-rich-fixtures.test.ts` passed: 35 tests.
- `pnpm --filter @oh-my-class/renderer build` passed.
- `lsp_diagnostics` on `packages/renderer/__tests__/current-renderer-baselines.test.ts` reported no diagnostics.

Note: focused renderer tests still emit the existing `sanitize-html` warning about allowing `<style>` tags. This is pre-existing current-renderer behavior captured by the baseline and is not changed in Phase 0.

## Blocked by

None - can start immediately
