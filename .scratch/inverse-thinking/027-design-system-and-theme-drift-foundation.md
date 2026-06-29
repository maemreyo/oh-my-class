---
title: Design system and theme drift foundation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Create the design-system contract and theme drift checks needed before broad UI polish continues. The frontend skill requires a `DESIGN.md` before UI work, and AGENTS.md says `theme.json` is the single source of truth for brand tokens. Existing mode UI issues rely on this foundation but do not own the canonical design-system document or drift gate.

## Acceptance criteria

- [ ] A canonical `DESIGN.md` exists in the agreed location and documents tokens, typography, spacing, motion, responsive rules, accessibility, and accepted debt.
- [ ] `DESIGN.md` references `common/branding/kits/default`, `ocean`, and `forest` as theme sources.
- [ ] Theme CSS generation drift is checked in CI: generated CSS must match committed output.
- [ ] Raw hardcoded colors in production UI/components are rejected or explicitly allowed with rationale.
- [ ] New UI polish issues can cite `DESIGN.md` instead of inventing local visual rules.

## Detailed test suite

- [ ] Design coverage script: Given production UI/components/templates, when scanning token usage, then every CSS variable used is declared in `DESIGN.md` or theme JSON.
- [ ] Theme drift test: Given a theme JSON edit without regenerating CSS, when the drift checker runs, then it fails with a diff.
- [ ] Theme drift test: Given manual CSS edit without theme JSON change, when the checker runs, then it fails.
- [ ] Token lint: Production UI component files fail if they introduce raw hex colors outside approved theme files.
- [ ] Accessibility baseline: `DESIGN.md` documents focus, contrast, reduced motion, and CJK/Vietnamese text requirements; a docs test checks these headings exist.
- [ ] Visual fixture: Render one artifact in default/ocean/forest and assert theme token classes/variables are present and no external assets are introduced.

## Blocked by

None - can start immediately
