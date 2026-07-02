---
title: Port Artifact UI CSS into renderer package
status: ready-for-agent
labels: [renderer, css, foundation]
created: 2026-07-02
---

## Parent

ADR-024: Artifact UI Renderer Integration

## What to build

Port the 10 CSS files from `.scratch/artifact-ui-integrations/resources/artifact-ui/` into `packages/renderer/src/artifact-ui/`. This is the foundation layer — no TypeScript code, no templates, no contract wiring. Just CSS files in the right place with the right structure.

Source files to port:
- `tokens/contract.css` → `src/artifact-ui/tokens/contract.css`
- `tokens/navy-ticket.css` → `src/artifact-ui/tokens/navy-ticket.css`
- `tokens/paper-dossier.css` → `src/artifact-ui/tokens/paper-dossier.css`
- `tokens/transit-route.css` → `src/artifact-ui/tokens/transit-route.css`
- `tokens/investigation-folder.css` → `src/artifact-ui/tokens/investigation-folder.css`
- `primitives.css` → `src/artifact-ui/primitives.css`
- `families/navy-ticket.css` → `src/artifact-ui/families/navy-ticket.css`
- `families/paper-dossier.css` → `src/artifact-ui/families/paper-dossier.css`
- `families/transit-route.css` → `src/artifact-ui/families/transit-route.css`
- `families/investigation-folder.css` → `src/artifact-ui/families/investigation-folder.css`

## Acceptance criteria

- [ ] All 10 CSS files exist at the correct paths under `packages/renderer/src/artifact-ui/`
- [ ] CSS files are byte-identical to the source (no modifications during port)
- [ ] `tokens/contract.css` defines the `--art-*` semantic token contract
- [ ] Each family token file (`tokens/{family}.css`) implements the contract via `data-artifact-theme` selector
- [ ] `primitives.css` uses only `--art-*` tokens (no hardcoded hex, no `--color-*` references)
- [ ] Each family component file (`families/{family}.css`) uses only `--art-*` tokens
- [ ] No `http://` or `https://` references in any CSS file
- [ ] No `@import url()` or `@font-face` with remote URLs
- [ ] CSS files are excluded from TypeScript compilation (`.css` not imported in `.ts` files yet)

## Detailed test suite

- [ ] `packages/renderer/__tests__/artifact-ui/css-invariants.test.ts`: greps all CSS files for `http://`, `https://`, `@import url(`, `@font-face` — expects zero matches
- [ ] `packages/renderer/__tests__/artifact-ui/css-invariants.test.ts`: verifies `tokens/contract.css` defines all required semantic tokens (--art-bg, --art-surface, --art-accent, --art-positive, --art-caution, --art-critical, etc.)
- [ ] `packages/renderer/__tests__/artifact-ui/css-invariants.test.ts`: verifies each family token file overrides the contract tokens (not just inherits defaults)

## Verification

- `pnpm --filter @oh-my-class/renderer test` → all tests pass
- Manual: open `packages/renderer/src/artifact-ui/tokens/contract.css` in editor — confirms token contract structure
- Manual: `grep -r "http://" packages/renderer/src/artifact-ui/` → zero matches

## Blocked by

None — can start immediately. CSS files are ready in `.scratch/artifact-ui-integrations/resources/artifact-ui/`.
