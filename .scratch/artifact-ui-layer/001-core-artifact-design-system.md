---
title: Build core Artifact UI layer primitives from template corpus
status: ready-for-agent
labels: []
created: 2026-07-01
---

## Parent

ADR-023: Artifact UI Layer from Template Corpus

## What to build

Create the first reusable Artifact UI layer for generated teaching materials. Extract shared tokens and primitives from `docs/templates/*` into renderer-owned code and documentation without changing dashboard UI. Produce a standalone browser-visible component showcase that demonstrates the core primitives and proves they can render offline, print-safe, and responsive.

This issue is a foundation slice. It should not redesign every artifact output yet. It should make later artifact-family work easy by establishing the reusable language: artifact shell, cover/hero, section header, stat card, callout, content card, tag/stamp, table/comparison, sidebar/route nav, diagnostics panel, and teacher/student projection wrappers.

## Acceptance criteria

- [ ] `DESIGN.md` documents a separate Artifact UI layer distinct from Product UI, referencing ADR-023 and the template corpus.
- [ ] Renderer-owned artifact tokens exist for at least paper dossier, navy ticket, transit route, and investigation folder visual families.
- [ ] Core Artifact UI primitives render from typed inputs or explicit view models, not from raw pasted template HTML.
- [ ] A standalone component showcase renders all core primitives and at least one stateful example for passed, needs-review, and failed statuses.
- [ ] Showcase output contains no `http://` or `https://` references, no remote fonts, no CDN assets, and no external scripts.
- [ ] Showcase is visually QA'd at 375px, 768px, and 1280px with screenshots or saved artifact evidence.
- [ ] Tests cover standalone HTML invariants, brand string presence, and no external asset references.

## Blocked by

None - can start immediately
