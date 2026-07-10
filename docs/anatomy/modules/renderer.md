# Module: renderer

**Path:** `packages/renderer`
**Role:** Converts typed artifact JSON data into standalone, self-contained HTML using Eta templates + runtime CSS generation. Zero CDN, zero external assets, works offline.

## Public interface

- `renderArtifact(type, data)` → standalone HTML string (`src/renderer.ts`)
- `render({ kind, input, context })` → `{ html, manifest, diagnostics, metrics }` (`src/core/render.ts`)
- `renderArtifactUi({ family, kind, audience, ... })` → standalone HTML (`src/artifact-ui/renderer.ts`)
- `loadTheme(name)` → cached ThemeTokens CSS string (`src/theme/loader.ts`)
- `renderBatch(requests)` → batch rendering (`src/core/render.ts`)
- `agent-worker` — stdin/stdout JSON rendering protocol for subprocess use (`src/agent-worker.ts`)

## Internal structure

### src/ (169 files) — Core rendering engine

**Pipeline A (legacy)**: `renderArtifact()` → loadTheme → Eta render → sanitize → HTML
**Pipeline B (plugin)**: `render()` → plugin.schema.validate → themeResolver → plugin.adapt → Eta render → enforceAssetPolicy → sanitize → HTML
**Pipeline C (artifact UI)**: `renderArtifactUi()` → loadArtifactCSS → adapter.adapt → Eta render → sanitize → HTML

- `core/` — PluginRegistry, ThemeResolver, render pipeline, SanitizerPolicy, asset policy (INVARIANT-04), managed scripts (SHA-256 verified)
- `plugins/` — 18 registered plugins: quiz, lesson, worksheet, drill, recap, infographic, answer_key, flashcard_deck, reading_passage, exit_ticket, roadmap, teaching_pack, + 4 Artifact UI families (navy-ticket, paper-dossier, transit-route, investigation-folder)
- `theme/` — 3-tier ThemeTokens (primitives → semantic → component), 4 themes (default, ocean, forest, high-contrast-dyslexia), runtime CSS generation
- `sanitizer/` — 12 per-artifact-type sanitize-html configs
- `contracts/` — TypeScript interfaces: ArtifactDataMap (13 types), ContentComponent (22 variants), 40+ question types across 8 families
- `scoring/` — 4 strategies: allOrNothing, partialCredit, vietnameseTF2025 (MOET Decision 764), rubricScoring
- `artifact-ui/` — 4 visual families with per-family CSS tokens + adapters
- `exporters/` — PPTX (pptxgenjs), JSON, QTI v3.0, VariantGenerator
- `design-kit/` — Extract CSS vars from HTML, map to ThemeTokens
- `diagrams/` — LLM-generated SVG diagrams with sanitizer
- `i18n/` — Vietnamese + English message catalog
- `preview-server/` — Express server for sandboxed preview (CSP headers, iframe sandbox)

### templates/ (69 files)

- `base.html` — HTML shell: DOCTYPE, theme CSS injection, header/brand, main content slot, footer, print styles
- `pages/` — 13 page templates (lesson, quiz, drill, worksheet, recap, infographic, answer_key, flashcard_deck, reading_passage, exit_ticket, teaching_pack, slide_deck, roadmap)
- `components/` — 43 reusable component templates (question types, grids, timelines, callouts, feedback, dispatchers)
- `artifact/` — 10 Artifact UI templates across 4 families

### Security layers

1. Eta auto-escaping (`<%= %>` escapes HTML entities)
2. Per-artifact-type HTML sanitization (12 configs)
3. INVARIANT-04: external URL regex rejection + managed script SHA-256 verification
4. CSP headers on preview server
5. iframe sandbox (never `allow-scripts` + `allow-same-origin` together)
6. SVG sanitizer (strips scripts/foreignObject)
7. Student-safe projection (strips answer/teacher-only data)

## Depends on

- **`schemas`** — imports ArtifactContentSchema and related generated types (8 imports)
- external: `eta` (^3.0.0), `sanitize-html` (^2.17.5), `zod` (^3.23.0), `pptxgenjs` (^4.0.1), `fflate` (^0.8.3), `express` (^5.2.1)

## Used by

- **`web`** — imports renderer for preview rendering (35 imports from schemas, 3 from renderer)
- **`exporters`** — type imports from `renderer/contracts/questions/*` (47 imports), runtime `renderBatch()` for vocabulary batch
- **`agents`** — imports `renderArtifact()` and `SlideDeckData` projection (9 imports)

## Data & side effects

- Reads: ThemeTokens JSON files from disk, template files from `templates/`, managed scripts
- Writes: None (pure transformation)
- Network calls: None

---

_Traced from source on 2026-07-10. Files examined in depth: all 169 source files + 70 template files. The plugin system (18 plugins) and theme system (3-tier tokens) are the most architecturally significant subsystems._
