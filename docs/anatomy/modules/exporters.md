# Module: exporters

**Path:** `packages/exporters`
**Role:** Exports teaching pack artifacts to external formats (GIFT for Moodle, H5P for interactive HTML5, Anki APKG, flashcard TSV, Google Forms). Two-layer design: stubs accept ArtifactContent[], real implementations accept BaseQuestion[], bridged via CLI subprocess.

## Public interface

- `exportByFormat(format, artifacts)` → Buffer (unified export router) (`src/index.ts`)
- `GIFTExporter.export(questions, category?)` → GIFT text string (`src/gift-impl/index.ts`)
- `H5PExporter.exportQuestion(question)` / `.exportFlashcards(deck)` / `.exportRecapSummary(recap)` → .h5p ZIP (`src/h5p-impl/index.ts`)
- `AnkiApkgExporter.exportDeck(deck)` → .apkg ZIP (`src/anki-apkg/index.ts`)
- `FlashcardTSVExporter.exportDeck(deck)` → TSV string (`src/flashcard-tsv/index.ts`)
- `GoogleFormsExporter.exportQuestions(title, questions, pointsPerQuestion)` → Google Form (`src/google-forms/index.ts`)
- CLI bridges: `src/cli.ts` (main), `src/vocabulary-batch/cli.ts` (vocab) — stdin/stdout JSON protocol

## Internal structure

- `gift-impl/` — GIFT serializer: supports MCQ, MCQ-multiple, TF 4-item, short answer, cloze, matching, essay
- `h5p-impl/` — H5P packager: builds h5p.json + content/content.json ZIP via fflate; supports MultiChoice, TrueFalse, Blanks, Flashcards, Summary
- `anki-apkg/` — Anki 2.1 SQLite schema via sql.js + ZIP via fflate
- `flashcard-tsv/` — Tab-separated values for Quizlet/Anki import
- `google-forms/` — OAuth 2.0 REST client: createForm, batchUpdate, listResponses; response normalization with FNV-1a pseudonymization
- `inverse-thinking.ts` — Multi-format exporter for inverse-thinking packs (GIFT/QTI implemented, H5P throws)
- `vocabulary-batch/` — Multi-cluster ZIP with HTML/GIFT/H5P per cluster + manifest

## Depends on

- **`renderer`** — type imports from `renderer/contracts/questions/*` (BaseQuestion, QuizData, FlashcardDeckData); runtime `renderBatch()` for vocabulary batch
- **`schemas`** — imports PracticeSet, SemanticAnchorCluster types
- external: `fflate` (ZIP), `sanitize-html`, `sql.js` (Anki SQLite)

## Used by

- **`gateway`** — `teaching_pack_export_writer.py` spawns Node CLI subprocess for GIFT/H5P/Anki/TSV exports; `vocabulary_batch_export.py` for vocabulary batch
- **`agents`** — `teaching_pack/exporters.py` references export formats

## Data & side effects

- Network calls: Google Forms OAuth (googleapis.com) — only in live Google Forms flow
- CLI subprocesses: stdin JSON → stdout JSON, invoked by Python gateway

---

_Traced from source on 2026-07-10. Files examined: all 47 files. Key insight: GIFT/H5P facades are stubs (throw UnsupportedFormatError); real implementations accept BaseQuestion[] via CLI bridge._
