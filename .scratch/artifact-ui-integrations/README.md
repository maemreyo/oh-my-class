# Artifact UI Integration Epic

## ADRs

- `docs/adr/023-artifact-ui-layer.md` — Artifact UI layer from template corpus (parent)
- `docs/adr/024-artifact-ui-renderer-integration.md` — Renderer integration architecture

## Goal

Integrate the Artifact UI CSS design system from `.scratch/artifact-ui-integrations/resources/` into `packages/renderer/`. Replace existing inline renderers (`semantic-anchor-projections.ts`, `inverse-thinking-renderer.ts`) with Artifact UI rendering. Establish a scalability pattern so adding a new artifact UI family requires minimal new code.

## Resources inventory

The `resources/artifact-ui/` directory contains production-ready CSS + interactivity JS:

| Category | Files | Lines | Status |
|----------|-------|-------|--------|
| Token CSS (contract + 4 families) | 5 | ~483 | Production-ready |
| Core primitives CSS | 1 | ~550 | Production-ready (includes 7 new primitives from Issue 004) |
| Family component CSS | 4 | ~371 | Production-ready |
| Interactivity JS | 1 | 310 | Production-ready (vanilla, no eval, no remote src) |
| Render harness (JS) | 1 | 187 | Simulation only |
| Page generators (JS) | 10 | ~1,500 | Simulation only |
| Built HTML demos | 13 | — | Generated |
| Documentation | 4 | — | Complete |
| Screenshots | 18 | — | Playwright-verified |

## Design Principles

1. **Family-registry pattern** — Adding a new family = CSS + templates + adapter + registry entry. No changes to loader, renderer, or existing families.
2. **CSS namespace isolation** — `--art-*` tokens never collide with `--color-*` tokens. Two independent token systems coexist.
3. **Contracts-first rendering** — Each family adapter transforms typed contracts into template data. No raw HTML editing.
4. **Standalone HTML invariant** — All output is self-contained: CSS inlined, no CDN, no external assets, works offline.
5. **Teacher/student projection safety** — ADR-022 enforced by adapter layer, not CSS hiding. Student files never contain teacher-only DOM.

## Issues

### Foundation (Wave 0-3)
1. `001-port-css-foundation.md` — Port 10 CSS files into renderer package
14. `014-port-interactivity-and-sanitizer.md` — Port interactivity.js + `sanitizeArtifactUi()` (runs in parallel with 001)
15. `015-root-cause-session-contract.md` — Define `RootCauseSessionData` TypeScript contract (no deps, start immediately)
2. `002-family-registry-and-css-loader.md` — Family registry + CSS loader (extensible pattern)
16. `016-css-loader-memoization.md` — CSS loader memoization for batch export performance
3. `003-eta-templates-all-families.md` — Eta templates for all 4 families (9 templates incl. root-cause-session)
17. `017-investigation-folder-frame-variants.md` — Specify detective/neutral frame as template conditional
4. `004-contract-adapters-all-families.md` — Contract adapters for all 4 families
7. `007-public-api-render-artifact-ui.md` — Public API + renderArtifactUi() + renderArtifactUiSet() entry points

### Migration (Wave 4-5)
5. `005-replace-semantic-anchor-renderer.md` — Replace semantic-anchor-projections.ts (navy-ticket)
6. `006-replace-inverse-thinking-renderer.md` — Replace inverse-thinking-renderer.ts (investigation-folder)
12. `012-wire-agent-renderer-paper-dossier.md` — Wire agent-renderer.ts lesson/answer_key → paper-dossier (audience: student)
13. `013-create-transit-route-artifact-type.md` — Create transit-route video-route (new, not replacement)

### Wiring (Wave 5-6)
11. `011-wire-vocabulary-batch-exporter.md` — Wire vocabulary batch exporter → renderArtifactUiSet()

### Quality (Wave 6-7)
8. `008-full-tdd-test-suite.md` — Full TDD test suite (~60 test cases)
9. `009-visual-qa-playwright.md` — Visual QA at 375/768/1280 (32 screenshots)
10. `010-scalability-validation.md` — Add-a-family checklist + docs (4 artifacts, no sanitizer per-family)

## Dependency order

```
Wave 0: 001 (CSS foundation)
        014 (interactivity.js + sanitizeArtifactUi) ← no deps, parallel with 001
        015 (RootCauseSessionData contract)          ← no deps, parallel with 001

Wave 1: 002 (registry + loader) ← 001
        016 (CSS loader memoization) ← 002

Wave 2: 003 (templates) ← 002, 015        [now 9 templates incl. root-cause-session]
        017 (frame variant spec) ← 003     [resolves open design question in 006]
        004 (adapters) ← 001, 015, 017

Wave 3: 007 (public API: renderArtifactUi + renderArtifactUiSet) ← 002, 003, 004, 014

Wave 4: 005 (replace vocabulary renderer) ← 007
         006 (replace inverse-thinking renderer) ← 007, 017
         012 (wire paper-dossier, audience: student) ← 007
         013 (create transit-route) ← 007

Wave 5: 011 (wire vocabulary exporter via renderArtifactUiSet) ← 005, 007

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
├── interactivity.js          ← ported by Issue 014
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
├── loader.ts                 ← memoized by Issue 016
└── index.ts                  ← exports renderArtifactUi + renderArtifactUiSet

packages/renderer/src/contracts/
└── root-cause-session.ts     ← added by Issue 015

packages/renderer/src/sanitizer/
└── configs/
    └── artifact-ui.ts        ← added by Issue 014 (ARTIFACT_UI_CONFIG + sanitizeArtifactUi)

packages/renderer/templates/artifact/
├── navy-ticket/
│   ├── teaching.teacher.html
│   ├── teaching.student.html
│   ├── practice.teacher.html
│   └── practice.student.html
├── paper-dossier/
│   ├── lesson.html
│   ├── answer-key.html
│   └── root-cause-session.html  ← added (Issue 003, contract from Issue 015)
├── transit-route/
│   └── video-route.html
└── investigation-folder/
    └── inverse-thinking.html    ← single template with frameVariant conditional (Issue 017)
```

## Key cross-epic references

- `vocabulary-batch/009` — existing semantic-anchor projections (to be replaced by 005)
- `packages/exporters/src/vocabulary-batch/` — vocabulary batch exporter (wired by 011)
- `inverse-thinking/` — existing inverse-thinking renderer (to be replaced by 006)
- `packages/renderer/src/agent-renderer.ts` — bridge for lesson/answer_key (wired by 012)
- ADR-022 — semantic anchor domain model and projection safety
- ADR-023 — artifact UI layer from template corpus
- `packages/renderer/src/theme/` — existing three-tier token system (coexists with `--art-*`)
