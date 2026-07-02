# Artifact UI Integration Epic

## ADRs

- `docs/adr/023-artifact-ui-layer.md` — Artifact UI layer from template corpus (parent)
- `docs/adr/024-artifact-ui-renderer-integration.md` — Renderer integration architecture

## Goal

Integrate the Artifact UI CSS design system from `.scratch/artifact-ui-integrations/resources/` into `packages/renderer/`. Replace existing inline renderers (`semantic-anchor-projections.ts`, `inverse-thinking-renderer.ts`) with Artifact UI rendering. Establish a scalability pattern so adding a new artifact UI family requires minimal new code.

## Design Principles

1. **Family-registry pattern** — Adding a new family = CSS + templates + adapter + registry entry. No changes to loader, renderer, or existing families.
2. **CSS namespace isolation** — `--art-*` tokens never collide with `--color-*` tokens. Two independent token systems coexist.
3. **Contracts-first rendering** — Each family adapter transforms typed contracts into template data. No raw HTML editing.
4. **Standalone HTML invariant** — All output is self-contained: CSS inlined, no CDN, no external assets, works offline.
5. **Teacher/student projection safety** — ADR-022 enforced by adapter layer, not CSS hiding. Student files never contain teacher-only DOM.

## Issues

### Foundation (Wave 0-3)
1. `001-port-css-foundation.md` — Port 10 CSS files into renderer package
2. `002-family-registry-and-css-loader.md` — Family registry + CSS loader (extensible pattern)
3. `003-eta-templates-all-families.md` — Eta templates for all 4 families (8 templates)
4. `004-contract-adapters-all-families.md` — Contract adapters for all 4 families
7. `007-public-api-render-artifact-ui.md` — Public API + renderArtifactUi() entry point

### Migration (Wave 4-5)
5. `005-replace-semantic-anchor-renderer.md` — Replace semantic-anchor-projections.ts (navy-ticket)
6. `006-replace-inverse-thinking-renderer.md` — Replace inverse-thinking-renderer.ts (investigation-folder)
12. `012-wire-agent-renderer-paper-dossier.md` — Wire agent-renderer.ts lesson/answer_key → paper-dossier
13. `013-create-transit-route-artifact-type.md` — Create transit-route video-route (new, not replacement)

### Wiring (Wave 5-6)
11. `011-wire-vocabulary-batch-exporter.md` — Wire vocabulary batch exporter → renderArtifactUi()

### Quality (Wave 6-7)
8. `008-full-tdd-test-suite.md` — Full TDD test suite (~50 test cases)
9. `009-visual-qa-playwright.md` — Visual QA at 375/768/1280 (24 screenshots)
10. `010-scalability-validation.md` — Add-a-family checklist + docs

## Dependency order

```
Wave 0: 001 (CSS foundation)

Wave 1: 002 (registry + loader) ← 001

Wave 2: 003 (templates) ← 002; 004 (adapters) ← 001

Wave 3: 007 (public API) ← 002, 003, 004

Wave 4: 005 (replace vocabulary renderer) ← 007
         006 (replace inverse-thinking renderer) ← 007
         012 (wire paper-dossier) ← 007
         013 (create transit-route) ← 007

Wave 5: 011 (wire vocabulary exporter) ← 005, 007

Wave 6: 008 (test suite) ← 005, 006, 011, 012, 013
         009 (visual QA) ← 007

Wave 7: 010 (scalability docs) ← 008, 009
```

## Folder structure (target)

```
packages/renderer/src/artifact-ui/
├── tokens/
│   ├── contract.css
│   ├── navy-ticket.css
│   ├── paper-dossier.css
│   ├── transit-route.css
│   └── investigation-folder.css
├── primitives.css
├── families/
│   ├── navy-ticket.css
│   ├── paper-dossier.css
│   ├── transit-route.css
│   └── investigation-folder.css
├── adapters/
│   ├── index.ts
│   ├── navy-ticket.ts
│   ├── paper-dossier.ts
│   ├── transit-route.ts
│   └── investigation-folder.ts
├── registry.ts
├── loader.ts
└── index.ts

packages/renderer/templates/artifact/
├── navy-ticket/
│   ├── teaching.teacher.html
│   ├── teaching.student.html
│   ├── practice.teacher.html
│   └── practice.student.html
├── paper-dossier/
│   ├── lesson.html
│   └── answer-key.html
├── transit-route/
│   └── video-route.html
└── investigation-folder/
    └── inverse-thinking.html
```

## Key cross-epic references

- `vocabulary-batch/009` — existing semantic-anchor projections (to be replaced by 005)
- `packages/exporters/src/vocabulary-batch/` — vocabulary batch exporter (wired by 011)
- `inverse-thinking/` — existing inverse-thinking renderer (to be replaced by 006)
- `packages/renderer/src/agent-renderer.ts` — bridge for lesson/answer_key (wired by 012)
- ADR-022 — semantic anchor domain model and projection safety
- ADR-023 — artifact UI layer from template corpus
- `packages/renderer/src/theme/` — existing three-tier token system (coexists with `--art-*`)
