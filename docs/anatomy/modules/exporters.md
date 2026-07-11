# Module: exporters

**Path:** `packages/exporters`
**Role:** Export format generators that convert ArtifactContent JSON to GIFT, H5P, QTI, Anki, flashcard TSV, PPTX, and Google Forms formats, with a two-layer design: stubs accept `ArtifactContent[]`, real implementations accept `BaseQuestion[]`, bridged via CLI subprocess.

## Public interface

| Symbol | Kind | File | Description |
|--------|------|------|-------------|
| `exportByFormat()` | async function | `src/index.ts:71` | Unified export entry: `ExportFormat` + `ArtifactContent[]` → `Buffer` |
| `ExportFormat` | type | `src/index.ts:27` | Union: `"html" \| "gift" \| "h5p" \| "qti" \| "anki_apkg" \| "flashcard_tsv" \| "pptx"` |
| `UnsupportedFormatError` | class | `src/qti/qti.ts:13` | Error thrown for unimplemented export formats |
| `GIFTExporter` | class | `src/gift-impl/index.ts:80` | Real GIFT serialiser: `BaseQuestion[]` → Moodle GIFT text |
| `H5PExporter` | class | `src/h5p-impl/index.ts:14` | Real H5P exporter: question → H5P ZIP package |
| `AnkiApkgExporter` | class | `src/anki-apkg/index.ts:204` | Anki .apkg exporter via sql.js + fflate |
| `exportApkg()` | async function | `src/anki-apkg/index.ts:155` | Low-level: `AnkiCard[]` → `.apkg` ZIP |
| `FlashcardTSVExporter` | class | `src/flashcard-tsv/index.ts:10` | TSV flashcard exporter for Quizlet/Anki import |
| `GoogleFormsExporter` | class | `src/google-forms/index.ts:49` | Google Forms API client + question mapper |
| `createGoogleFormsClient()` | function | `src/google-forms/client.ts:44` | Creates Forms API client from access token |
| `getAuthUrl()` | function | `src/google-forms/auth.ts:34` | Google OAuth 2.0 consent URL builder |
| `exchangeCode()` | async function | `src/google-forms/auth.ts:46` | OAuth code → token exchange |
| `refreshAccessToken()` | async function | `src/google-forms/auth.ts:69` | OAuth token refresh |
| `extractQuestions()` | function | `src/cli.ts:38` | CLI utility: `ArtifactEntry[]` → `BaseQuestion[]` |
| `exportInverseThinkingGift()` | function | `src/inverse-thinking.ts:70` | Inverse-thinking → GIFT format |
| `exportInverseThinkingH5P()` | async function | `src/inverse-thinking.ts:87` | Inverse-thinking → H5P (throws Unsupported) |
| `exportInverseThinkingQTI()` | function | `src/inverse-thinking.ts:91` | Inverse-thinking → QTI XML |
| `buildInverseThinkingGoogleFormsRequests()` | function | `src/inverse-thinking.ts:103` | Inverse-thinking → Forms batchUpdate requests |
| `supportForInverseThinking()` | function | `src/inverse-thinking.ts:62` | Format support lookup |
| `INVERSE_THINKING_FORMAT_SUPPORT` | const | `src/inverse-thinking.ts:54` | Format support matrix |
| `UnsupportedInverseThinkingExportError` | class | `src/inverse-thinking.ts:42` | Error for unsupported inverse-thinking exports |
| `buildVocabularyBatchPackage()` | async function | `src/vocabulary-batch/index.ts:196` | Vocabulary batch → ZIP with HTML/GIFT/H5P per cluster |

### Re-exported types (from `src/vocabulary-batch/index.ts`)

- `VocabularyBatchExportFormat`, `VocabularyBatchClusterInput`, `VocabularyBatchPackageOptions`
- `VocabularyBatchPackage`, `VocabularyBatchManifest`, `VocabularyBatchManifestCluster`, `VocabularyBatchManifestFile`

## Internal structure

### Stubs vs real implementations (two-layer design)

The `index.ts` API surface uses `ArtifactContent[]` as input. The stubs (`gift/gift.ts`, `h5p/h5p.ts`, `qti/qti.ts`) all throw `UnsupportedFormatError` — they exist to document the planned API but are not wired. The real implementations live in `gift-impl/`, `h5p-impl/`, and accept `BaseQuestion[]` (from `@oh-my-class/renderer` contracts).

The CLI bridge (`cli.ts`) bridges the gap: it receives `ArtifactEntry[]` via stdin, calls `extractQuestions()` to flatten into `BaseQuestion[]`, and invokes the real exporters.

### Format implementations

| Directory | Format | Status | Input type |
|-----------|--------|--------|-----------|
| `gift/gift.ts` | GIFT stub | Throws `UnsupportedFormatError` | `ArtifactContent[]` |
| `gift-impl/index.ts` | GIFT real | Working | `BaseQuestion[]` (MCQ, TF, SA, Cloze, Match, Essay) |
| `h5p/h5p.ts` | H5P stub | Throws `UnsupportedFormatError` | `ArtifactContent[]` |
| `h5p-impl/index.ts` | H5P real | Working | `BaseQuestion[]` + `FlashcardDeckData` + `RecapData` |
| `h5p-impl/packager.ts` | H5P ZIP packager | Working | `h5p.json` + `content/content.json` + library files |
| `h5p-impl/content-types/` | H5P content type converters | Working | `multi-choice.ts`, `true-false.ts`, `flashcards.ts`, `summary.ts`, `blanks.ts` |
| `qti/qti.ts` | QTI stub | Throws `UnsupportedFormatError` | `ArtifactContent[]` |
| `anki-apkg/index.ts` | Anki .apkg | Working | `FlashcardDeckData` → SQLite + ZIP |
| `flashcard-tsv/index.ts` | TSV flashcards | Working | `FlashcardDeckData` → tab-separated |
| `google-forms/` | Google Forms API | Working | `BaseQuestion[]` → Forms batchUpdate |
| `inverse-thinking.ts` | Inverse-thinking exports | Partial (GIFT + QTI work, H5P unsupported) | `InverseThinkingPack` |
| `vocabulary-batch/` | Vocabulary batch ZIP | Working | `SemanticAnchorCluster[]` → ZIP with HTML/GIFT/H5P |

### Google Forms sub-system (`src/google-forms/`)

| File | Responsibility |
|------|---------------|
| `auth.ts` | OAuth 2.0 flow: consent URL, code exchange, token refresh (calls `oauth2.googleapis.com`) |
| `client.ts` | `GoogleFormsClient` — Forms API wrapper (`forms.googleapis.com/v1/forms`) |
| `question-mapper.ts` | `questionToFormsItem()` — `BaseQuestion` → `FormsItem` (MCQ, TF, SA, Essay) |
| `index.ts` | `GoogleFormsExporter` — orchestrates create form → batch update → list responses |

### CLI bridge (`src/cli.ts`)

Invoked by the Python export adapter (`teaching_pack_export_writer.py`) via subprocess:
- **Input** (stdin JSON): `{ format, run_id, artifacts, output_dir }`
- **Output** (stdout JSON): `{ path }` on success
- **Fail-closed**: any error writes nothing and exits non-zero
- Handles: `gift`, `h5p`, `qti`, `pptx`, `anki_apkg`, `flashcard_tsv`

### Shared utilities

- `extractQuestions(artifacts)` (`src/cli.ts:38`) — flattens `ArtifactEntry[]` → `BaseQuestion[]` by scanning `sections[].questions[]`
- `buildDeck(run_id, artifacts)` (`src/cli.ts:144`) — builds `FlashcardDeckData` from `flashcard_deck` artifacts or falls back to quiz/drill Q&A pairs

## Depends on

- **`renderer`** — ~24 import lines across 9 files; question types, slide deck data, render functions
- **`schemas`** — 5 import lines across 4 files; ArtifactContent, SemanticAnchorCluster

| Dependency | Kind | Import sites | Verified |
|-----------|------|-------------|----------|
| `@oh-my-class/renderer` (workspace) | runtime | See table below | ✅ |
| `@oh-my-class/schemas` (workspace) | devDependency | `src/index.ts:8`, `src/gift/gift.ts:12`, `src/h5p/h5p.ts:11`, `src/qti/qti.ts:11`, `src/vocabulary-batch/index.ts:2` | ✅ |
| `fflate` (npm) | runtime | `src/anki-apkg/index.ts:9`, `src/vocabulary-batch/index.ts:1` — ZIP compression | ✅ |
| `sql.js` (npm) | runtime | `src/anki-apkg/index.ts:8` — SQLite in WASM for Anki .apkg | ✅ |
| `sanitize-html` (npm) | runtime | `package.json:14` | ✅ |

### Detailed renderer imports

| Import site | What is imported |
|-------------|-----------------|
| `src/cli.ts:13` | `BaseQuestion` from `@oh-my-class/renderer/contracts/questions/base.js` |
| `src/cli.ts:14` | `SlideDeckData` from `@oh-my-class/renderer/contracts/slide_deck.js` |
| `src/cli.ts:97` | `QTIExporter` from `@oh-my-class/renderer/exporters/qti/index.js` |
| `src/cli.ts:108` | `PPTXExporter` from `@oh-my-class/renderer/exporters/pptx/index.js` |
| `src/gift-impl/index.ts:1` | `BaseQuestion` from `@oh-my-class/renderer/contracts/questions/base.js` |
| `src/gift-impl/index.ts:2-3` | `MultipleChoiceSingle`, `MultipleChoiceMultiple`, `TrueFalse4Item` from `@oh-my-class/renderer/contracts/questions/types/choice.js` |
| `src/gift-impl/index.ts:5` | `ShortAnswer`, `Cloze` from `@oh-my-class/renderer/contracts/questions/types/text-entry.js` |
| `src/gift-impl/index.ts:6` | `Matching` from `@oh-my-class/renderer/contracts/questions/types/match.js` |
| `src/gift-impl/index.ts:7` | `Essay` from `@oh-my-class/renderer/contracts/questions/types/open.js` |
| `src/gift-impl/index.ts:8` | `QuizData` from `@oh-my-class/renderer/contracts/quiz.js` |
| `src/h5p-impl/index.ts:1` | `BaseQuestion` from `@oh-my-class/renderer/contracts/questions/base.js` |
| `src/h5p-impl/index.ts:2` | `MultipleChoiceSingle`, `MultipleChoiceMultiple`, `TrueFalse4Item` from `@oh-my-class/renderer/contracts/questions/types/choice.js` |
| `src/h5p-impl/index.ts:3` | `Cloze` from `@oh-my-class/renderer/contracts/questions/types/text-entry.js` |
| `src/h5p-impl/index.ts:4` | `ClozeMixed`, `FillBlankWordBank` from `@oh-my-class/renderer/contracts/questions/types/fill-gap.js` |
| `src/h5p-impl/index.ts:5` | `FlashcardDeckData` from `@oh-my-class/renderer/contracts/flashcard_deck.js` |
| `src/h5p-impl/index.ts:6` | `RecapData` from `@oh-my-class/renderer/contracts/recap.js` |
| `src/anki-apkg/index.ts:10` | `FlashcardDeckData`, `Flashcard` from `@oh-my-class/renderer/contracts/flashcard_deck.js` |
| `src/flashcard-tsv/index.ts:1` | `FlashcardDeckData`, `Flashcard` from `@oh-my-class/renderer/contracts/flashcard_deck.js` |
| `src/google-forms/question-mapper.ts:1` | `BaseQuestion` from `@oh-my-class/renderer/contracts/questions/base.js` |
| `src/google-forms/question-mapper.ts:2` | `MultipleChoiceSingle`, `MultipleChoiceMultiple`, `TrueFalse4Item` from `@oh-my-class/renderer/contracts/questions/types/choice.js` |
| `src/google-forms/question-mapper.ts:3` | `ShortAnswer` from `@oh-my-class/renderer/contracts/questions/types/text-entry.js` |
| `src/google-forms/question-mapper.ts:4` | `Essay` from `@oh-my-class/renderer/contracts/questions/types/open.js` |
| `src/google-forms/index.ts:1` | `BaseQuestion` from `@oh-my-class/renderer/contracts/questions/base.js` |
| `src/google-forms/index.ts:2` | `QuizData` from `@oh-my-class/renderer/contracts/quiz.js` |
| `src/vocabulary-batch/index.ts:3` | `renderBatch` from `@oh-my-class/renderer` |
| `src/vocabulary-batch/index.ts:4` | `RenderContext`, `RenderRequest`, `RenderResponse` from `@oh-my-class/renderer` |

**Total renderer imports: ~24 import lines across 9 files.** Phase 3 hypothesis of "48 imports" was overcounted — actual distinct type imports are ~20 unique symbols.

### Google Forms HTTP calls (external network)

| File:line | URL | Purpose |
|----------|-----|---------|
| `src/google-forms/auth.ts:43` | `https://accounts.google.com/o/oauth2/v2/auth` | OAuth consent URL |
| `src/google-forms/auth.ts:50` | `https://oauth2.googleapis.com/token` | Code → token exchange |
| `src/google-forms/auth.ts:73` | `https://oauth2.googleapis.com/token` | Token refresh |
| `src/google-forms/client.ts:3` | `https://forms.googleapis.com/v1/forms` | Forms API base URL |

## Used by

- **`gateway`** — CLI bridge invoked via subprocess by teaching_pack_export_writer
- **`agents`** — test-only import (tests/test_flashcard_export_e2e.py)

| Consumer | Import site | Usage |
|---------|-------------|-------|
| **gateway** | `services/gateway/teaching_pack_export_writer.py` (via subprocess) | CLI bridge invoked by Python export adapter |
| **agents** | `tests/test_flashcard_export_e2e.py` (test only) | Integration test for flashcard export |

## Data & side effects

- **Filesystem writes**: CLI writes exported files to `output_dir` (`src/cli.ts:70-138`)
- **Network**: Google Forms API calls (OAuth + Forms REST API) — `src/google-forms/auth.ts`, `src/google-forms/client.ts`
- **CLI**: `dist/index.js` is the entry point for subprocess invocation by the Python export adapter
- **In-memory state**: None (stateless exporters)

## Notes / discrepancies vs existing docs

1. **AGENTS.md §10 says "QTI returns an explicit unsupported error"** — confirmed: `src/qti/qti.ts:23-29` throws `UnsupportedFormatError`. However, the CLI bridge (`src/cli.ts:96-104`) imports `QTIExporter` from `@oh-my-class/renderer/exporters/qti/index.js` (renderer's own QTI exporter), NOT from `src/qti/qti.ts`. This means QTI export may actually work through the renderer's implementation, not the stub.

2. **AGENTS.md §10 says "GIFT coverage note: numerical type not supported by TS gift-impl"** — confirmed: `src/gift-impl/index.ts:67-77` only handles `multiple_choice_single`, `multiple_choice_multiple`, `true_false_4item`, `short_answer`, `cloze`, `matching`, `essay`. `numerical` is not in the switch.

3. **Phase 3 hypothesis "exporters → renderer: 48 imports"** — overcounted. Actual count is ~24 import lines across 9 files, ~20 unique type symbols. The heavy dependency is real but the number was inflated.

4. **Phase 3 hypothesis "exporters → schemas: 10 imports"** — close. Actual: 5 import lines across 4 files (`index.ts:8`, `gift/gift.ts:12`, `h5p/h5p.ts:11`, `qti/qti.ts:11`, `vocabulary-batch/index.ts:2`). All are `ArtifactContent` or `SemanticAnchorCluster`/`PracticeSet`.

5. **Phase 3 hypothesis "exporters → gateway: 1 import"** — DISPROVED. Zero imports from `services/gateway` in any exporters source file. The gateway calls the exporters via subprocess (CLI bridge), not via Python imports. This is a clean boundary.

6. **Phase 3 hypothesis "HTTP clients: google-forms/auth.ts calls oauth2.googleapis.com"** — CONFIRMED. `src/google-forms/auth.ts:50,73` calls `https://oauth2.googleapis.com/token`. Additionally, `src/google-forms/client.ts:3` calls `https://forms.googleapis.com/v1/forms`.

7. **Two GIFT/H5P paths exist**: The `gift/gift.ts` and `h5p/h5p.ts` stubs accept `ArtifactContent[]` and throw. The real `gift-impl/index.ts` and `h5p-impl/index.ts` accept `BaseQuestion[]` and work. The CLI bridge (`cli.ts`) uses the real implementations. The `exportByFormat()` function in `index.ts` uses the stubs.

---
_Traced from source on 2026-07-11. Files examined in depth: `src/index.ts`, `src/cli.ts`, `src/inverse-thinking.ts`, `src/gift/gift.ts`, `src/gift-impl/index.ts`, `src/h5p/h5p.ts`, `src/h5p-impl/index.ts`, `src/h5p-impl/packager.ts`, `src/h5p-impl/content-types/` (directory), `src/qti/qti.ts`, `src/anki-apkg/index.ts`, `src/flashcard-tsv/index.ts`, `src/google-forms/auth.ts`, `src/google-forms/client.ts`, `src/google-forms/question-mapper.ts`, `src/google-forms/index.ts`, `src/vocabulary-batch/index.ts`, `package.json`._
