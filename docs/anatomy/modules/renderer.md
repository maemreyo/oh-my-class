# Module: renderer

**Path:** `packages/renderer`
**Role:** Eta template engine that renders ArtifactContent JSON into standalone HTML with inlined CSS, no CDN dependencies, and print-ready output.

## Public interface

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `renderArtifact<T>()` | async function | `src/renderer.ts:72` | Main entry: type→data→standalone HTML (legacy path) |
| `render()` | async function | `src/core/render.ts:21` | Plugin-based render: `RenderRequest`→`RenderResponse` |
| `renderBatch()` | async function | `src/core/render.ts:137` | Parallel batch render |
| `renderTemplate()` | function | `src/renderer.ts:96` | Inline Eta template string render |
| `renderAgentArtifact()` | async function | `src/agent-renderer.ts:335` | CLI entry: ArtifactContent JSON→HTML via stdin |
| `PluginRegistry` | class | `src/core/registry.ts:4` | Artifact kind plugin registry (register/get/metadata) |
| `createPluginRegistry()` | function | `src/core/registry.ts:43` | Factory for `PluginRegistry` |
| `ThemeResolver` | type | `src/core/theme-resolver.ts` | Resolves theme tokens to CSS for a render context |
| `defaultThemeResolver` | const | `src/core/theme-resolver.ts` | Default theme resolver |
| `sanitizeRenderedHtml()` | function | `src/core/sanitizer.ts:50` | Per-artifact-type HTML sanitization (core pipeline) |
| `sanitize()` | function | `src/sanitizer/index.ts:42` | Legacy per-artifact-type sanitization |
| `enforceInlineOnlyAssetPolicy()` | function | `src/core/asset-policy.ts:45` | Throws on external assets (INVARIANT-04) |
| `inlineCss()` | function | `src/inline-assets.ts:8` | Inject `<style>` before `</head>` |
| `validateNoExternalUrls()` | function | `src/inline-assets.ts:17` | Regex scan for `http(s)://` in href/src |
| `loadManagedScripts()` | function | `src/core/managed-scripts.ts` | Load scripts declared by plugins |
| `hashManagedScriptSource()` | function | `src/core/managed-scripts.ts` | SHA-256 hash for script verification |
| `ExportWriter` | class | `src/exporters/export-writer.ts:12` | Render→ManifestStore bridge |
| `mountPreviewServer()` | function | `src/preview-server/index.ts:10` | Express `/api/preview/:runId` route |
| `PreviewStore` | class | `src/preview-server/store.ts` | TTL-based in-memory preview storage |
| `importDesignKit()` | async function | `src/design-kit/index.ts:21` | Import theme from HTML CSS variables |
| `loadTheme()` | function | `src/theme/loader.ts:40` | Load ThemeTokens JSON → CSS custom properties |
| `clearThemeCache()` | function | `src/theme/loader.ts:51` | Clear theme LRU cache |
| `ThemeCSSGenerator` | class | `src/theme/generator.ts` | 3-tier token→CSS generator |
| `projectSlideDeckSurface()` | function | `src/slide-deck-projection.ts:189` | Surface-aware slide deck projection (ADR-043) |
| `assertStudentSlideDeckHtmlIsSafe()` | function | `src/slide-deck-projection.ts:228` | Teacher-only leak guard (defense in depth) |
| Scoring strategies | functions | `src/scoring/index.ts` | `allOrNothing`, `partialCredit`, `vietnameseTF2025`, `rubricScoring` |
| Question type registry | class | `src/contracts/questions/registry.ts` | `QuestionTypeRegistry` — 50+ exercise types |

### Re-exported types (from `src/contracts/index.ts`)

- `ArtifactDataMap` — 13 artifact types mapped to their data interfaces
- `ArtifactType` — union of `keyof ArtifactDataMap`
- All individual data types: `LessonData`, `QuizData`, `DrillData`, `WorksheetData`, `RecapData`, `InfographicData`, `AnswerKeyData`, `FlashcardDeckData`, `ReadingPassageData`, `ExitTicketData`, `TeachingPackData`, `RoadmapData`, `SlideDeckData`
- 50+ question types from `contracts/questions/` (choice, text-entry, fill-gap, match, order, open, interactive, multimedia families)
- `VideoRouteData`, `RootCauseSessionData` (render-layer UI contracts)

### Re-exported types (from `src/core/types.ts`)

- `RenderRequest`, `RenderResponse`, `RenderContext`, `RenderManifest`
- `ArtifactKindPlugin<T>` — plugin interface (schema, adapt, templatePath, postSanitizeCheck)
- `PluginMetadata`, `RenderBatchRequest`, `RenderMetrics`, `RenderDiagnostic`
- `SanitizerPolicy`, `AudiencePolicy`, `RenderAssetPolicy`, `RenderAudience`, `RenderMode`, `RenderLocale`

## Internal structure

### Core render pipeline (`src/core/`)

| File | Responsibility |
|------|---------------|
| `render.ts` | Plugin dispatch: validates input via Zod, resolves theme, calls `plugin.adapt()`, renders via Eta, sanitizes, enforces asset policy, builds manifest |
| `registry.ts` | `PluginRegistry` — `Map<string, ArtifactKindPlugin>`, register/get/metadata |
| `runtime.ts` | `defaultRegistry` — 19 built-in plugins wired at import time |
| `types.ts` | All core interfaces (`RenderRequest`, `RenderResponse`, `ArtifactKindPlugin`, etc.) |
| `asset-policy.ts` | `enforceInlineOnlyAssetPolicy()` — regex scan for external URLs + managed script SHA-256 check |
| `sanitizer.ts` | `sanitizeRenderedHtml()` — per-artifact-type sanitize-html config dispatch |
| `managed-scripts.ts` | Load + SHA-256 hash for plugin-declared scripts |
| `theme-resolver.ts` | `ThemeResolver` — resolves theme tokens → CSS for a render context |
| `manifest-store.ts` | `ManifestStore` — in-memory render manifest + HTML storage |
| `errors.ts` | `RendererError`, `RendererErrorCategory`, `RendererErrorCode` |

### Plugins (`src/plugins/`)

19 artifact-kind plugins, each implementing `ArtifactKindPlugin<T>`:

`fixture`, `quiz`, `worksheet`, `drill`, `recap`, `infographic`, `lesson`, `answer-key`, `flashcard-deck`, `reading-passage`, `exit-ticket`, `roadmap`, `slide-deck`, `teaching-pack`, `navy-ticket.teaching`, `navy-ticket.practice`, `inverse-thinking`, `root-cause-session`, `video-route`

Each plugin declares: `kind`, `version`, `schema` (Zod), `audience`, `capabilities`, `sanitizerPolicy`, `adapt()`, `templatePath()`, and optionally `postSanitizeCheck()`.

### Artifacts data contracts (`src/contracts/`)

Self-contained TypeScript interfaces (NOT generated from Python contracts):

| File | Types |
|------|-------|
| `index.ts` | `ArtifactDataMap` — 13-type mapping |
| `lesson.ts` | `LessonData`, `LessonSection`, `VocabEntry` |
| `quiz.ts` | `QuizData`, `MCQuestion` |
| `drill.ts` | `DrillData`, `DrillQuestion` |
| `worksheet.ts` | `WorksheetData`, `WorksheetSection` |
| `recap.ts` | `RecapData`, `RecapItem` |
| `infographic.ts` | `InfographicData`, `InfographicSection` |
| `answer_key.ts` | `AnswerKeyData`, `AnswerKeySection`, `AnswerKeyMetadata` |
| `flashcard_deck.ts` | `FlashcardDeckData`, `Flashcard` |
| `reading_passage.ts` | `ReadingPassageData`, `ComprehensionQuestion` |
| `exit_ticket.ts` | `ExitTicketData`, `ExitTicketQuestion` |
| `roadmap.ts` | `RoadmapData`, `RoadmapHero`, `RoadmapSidebar`, `RoadmapSection` |
| `slide_deck.ts` | `SlideDeckData` + 15+ sub-types |
| `components.ts` | `ContentComponent`, `QuestionCardComponent`, `QuestionListComponent` |
| `questions/base.ts` | `BaseQuestion`, `BloomLevel`, `ScoringConfig` |
| `questions/types/` | `choice.ts`, `text-entry.ts`, `fill-gap.ts`, `match.ts`, `order.ts`, `open.ts`, `interactive.ts`, `multimedia.ts` |
| `schemas/` | `lesson-plan.ts`, `teaching-pack.ts`, `worksheet.ts`, `infographic.ts` |

### Theme system (`src/theme/`)

| File | Responsibility |
|------|---------------|
| `tokens.ts` | `ThemeTokens` interface (3-tier: `PrimitiveTokens`, `SemanticTokens`, `ComponentTokens`) |
| `generator.ts` | `ThemeCSSGenerator` — tokens → CSS custom properties |
| `loader.ts` | `loadTheme(name)` — reads JSON from `themes/`, generates CSS, caches |
| `themes/` | `default.json`, `ocean.json`, `forest.json`, `high-contrast-dyslexia.json` |

### HTML sanitization (`src/sanitizer/`)

Per-artifact-type `sanitize-html` configs:

`base-config.ts`, `quiz.js`, `drill.js`, `worksheet.js`, `recap.js`, `infographic.js`, `lesson.js`, `answer_key.js`, `flashcard_deck.js`, `reading_passage.js`, `exit_ticket.js`, `roadmap.js`, `artifact-ui.js`

### Slide deck projection (`src/slide-deck-projection.ts`)

Surface-aware projection implementing ADR-043 (5 surfaces: `student`, `presentation`, `print`, `teacher`, `review`). Strips teacher-only data for student-safe surfaces. `assertStudentSlideDeckHtmlIsSafe()` provides defense-in-depth leak detection.

### Export sub-system (`src/exporters/`)

| File | Responsibility |
|------|---------------|
| `export-writer.ts` | `ExportWriter` — render → `ManifestStore` bridge |
| `qti/index.ts` | `QTIExporter` — question types → QTI 2.1 XML |
| `pptx/index.ts` | `PPTXExporter` — `SlideDeckData` → PowerPoint |
| `json/` | JSON export utilities |
| `variant-generator/` | Audience-variant generation |

### Design kit (`src/design-kit/`)

`importDesignKit(html)` — extracts CSS variables from external HTML (regex or LLM), maps to `ThemeTokens`, validates. Used for theme import from existing materials.

### Preview server (`src/preview-server/`)

Express-based preview: `mountPreviewServer(app)` → `/api/preview/:runId`. `PreviewStore` with TTL-based expiry. `buildIframeEmbed()` for sandboxed iframe wrapping. `buildCSPHeader()` for CSP headers.

### Agent worker (`src/agent-worker.ts`, `src/agent-renderer.ts`)

CLI entry via `bin.omc-render`. `renderAgentArtifact()` dispatches ArtifactContent JSON through the plugin system. Supports `--worker` mode for long-running subprocess. Maps Python ArtifactContent fields to TypeScript renderer contracts.

## Depends on

| Dependency | Kind | Import sites | Verified |
|-----------|------|-------------|----------|
| `eta` (npm) | runtime | `src/eta-engine.ts:11` — `import { Eta } from "eta"` | ✅ |
| `zod` (npm) | runtime | `src/core/types.ts:1` — `import type { z } from "zod"` | ✅ |
| `sanitize-html` (npm) | runtime | `src/sanitizer/index.ts:1`, `src/core/sanitizer.ts:1` | ✅ |
| `express` (npm) | runtime | `src/preview-server/index.ts` — `import type { Application } from "express"` | ✅ |
| `fflate` (npm) | runtime | `package.json:28` — ZIP compression | ✅ |
| `pptxgenjs` (npm) | runtime | `package.json:29` — PowerPoint generation | ✅ |
| `@oh-my-class/schemas` (workspace) | devDependency | `src/agent-renderer.ts:3` — `ArtifactContentSchema`; `src/semantic-anchor-projections.ts:9` — `PracticeSet`, `SemanticAnchorCluster` | ✅ |

**No inbound imports from Python contracts.** The renderer's TypeScript contracts (`src/contracts/`) are self-contained interfaces, NOT generated from `common/contracts`. The only connection to `@oh-my-class/schemas` is via the devDependency (used for runtime validation in the agent worker).

## Used by

| Consumer | Import site | Usage |
|---------|-------------|-------|
| **exporters** | `packages/exporters/src/cli.ts:13-14` | Imports `BaseQuestion`, `SlideDeckData` from renderer contracts |
| **exporters** | `packages/exporters/src/gift-impl/index.ts:1-8` | Imports 8 question type interfaces |
| **exporters** | `packages/exporters/src/h5p-impl/index.ts:1-6` | Imports 6 question type interfaces |
| **exporters** | `packages/exporters/src/anki-apkg/index.ts:10` | Imports `FlashcardDeckData`, `Flashcard` |
| **exporters** | `packages/exporters/src/flashcard-tsv/index.ts:1` | Imports `FlashcardDeckData`, `Flashcard` |
| **exporters** | `packages/exporters/src/google-forms/question-mapper.ts:1-4` | Imports 4 question type interfaces |
| **exporters** | `packages/exporters/src/google-forms/index.ts:1-2` | Imports `BaseQuestion`, `QuizData` |
| **exporters** | `packages/exporters/src/vocabulary-batch/index.ts:3-4` | Imports `renderBatch`, `RenderContext`, `RenderRequest`, `RenderResponse` |
| **exporters** | `packages/exporters/src/cli.ts:97,108` | Imports `QTIExporter`, `PPTXExporter` from renderer/exporters |

## Data & side effects

- **Filesystem reads**: Theme JSON files from `themes/` directory (`src/theme/loader.ts:27`)
- **Filesystem reads**: Managed script source files from disk (`src/core/managed-scripts.ts`)
- **Network**: None (all assets inlined, INVARIANT-04)
- **Express routes**: `/api/preview/:runId` via `mountPreviewServer()` (`src/preview-server/index.ts:10`)
- **CLI**: `omc-render` binary — reads JSON from stdin, writes HTML to stdout (`src/agent-renderer.ts:378-385`)
- **In-memory state**: `ThemeCSSGenerator` LRU cache, `ManifestStore`, `PreviewStore`

## Notes / discrepancies vs existing docs

1. **AGENTS.md §11 says "13 page templates"** — actual count is 14 files in `templates/pages/` (13 `.html` templates + `slide-deck-player.js`). The count is correct.
2. **AGENTS.md §8.3 says canonical source is `packages/renderer/src/theme/themes/*.json`** — confirmed: `src/theme/loader.ts:17-19` resolves `THEMES_DIR` to `themes/` under the dist or source tree.
3. **Phase 3 hypothesis "renderer → schemas: 8 imports"** — partially correct. The renderer imports from `@oh-my-class/schemas` (the TS package, not the Python contracts) in 2 files: `agent-renderer.ts:3` and `semantic-anchor-projections.ts:9`. The bulk of schema-like types live in the renderer's own `src/contracts/` directory, which is self-contained.
4. **Phase 3 hypothesis "renderer → contracts: 1 import"** — INCORRECT. The renderer has zero imports from `common/contracts` (Python). The renderer's TypeScript contracts are defined locally in `src/contracts/`. The Python `contracts` package and TypeScript `schemas` package are separate codebases that define overlapping but non-identical shapes.
5. **Two render paths exist**: The legacy `renderArtifact()` path (type+data→HTML via Eta) and the newer `render()` path (plugin-based `RenderRequest`→`RenderResponse`). `agent-renderer.ts` uses both, with `render()` as the primary path for most artifact types and `renderArtifact()` only for `slide_deck`.
6. **19 plugins registered at import time** in `src/core/runtime.ts:19-39` — this is a runtime-wired dependency (plugin registration via function call, not DI).

---
_Traced from source on 2026-07-11. Files examined in depth: `src/renderer.ts`, `src/inline-assets.ts`, `src/eta-engine.ts`, `src/core/render.ts`, `src/core/registry.ts`, `src/core/types.ts`, `src/core/runtime.ts`, `src/core/asset-policy.ts`, `src/core/sanitizer.ts`, `src/sanitizer/index.ts`, `src/contracts/index.ts`, `src/contracts/questions/base.ts`, `src/contracts/questions/index.ts`, `src/theme/tokens.ts`, `src/theme/loader.ts`, `src/theme/index.ts`, `src/plugins/` (directory), `src/slide-deck-projection.ts`, `src/agent-renderer.ts`, `src/agent-component-projection.ts`, `src/agent-worker.ts`, `src/semantic-anchor-projections.ts`, `src/inverse-thinking-renderer.ts`, `src/design-kit/index.ts`, `src/preview-server/index.ts`, `src/exporters/export-writer.ts`, `src/scoring/index.ts`, `src/i18n/catalog.ts`, `src/diagrams/index.ts`, `templates/pages/` (directory), `package.json`._
