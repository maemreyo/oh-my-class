# ADR-031: Full Output Test Matrix (teacher-scenario e2e)

## Status

**Proposed** (2026-07-03) — Defines the complete set of outputs the teaching-pack system can
produce and mandates that the headless teacher-scenario driver (FFA-10) exercises **all** of
them — every artifact type, every wired export format, every pipeline mode, across the four
teacher decision scenarios. This is the definitive "full test". Companion to ADR-028/029/030.

## Context

Inspecting `packages/exporters/src/*` and the gateway export writer
(`services/gateway/teaching_pack_export_writer.py`) shows the producible outputs are broader
than ADR-030 captured. Without an explicit matrix, an e2e "full test" silently covers only a
subset (e.g. HTML + flashcards) and misses the assessment exports and alternate modes.

## The complete output matrix

**A. Standalone HTML** — every artifact type, `student` and `teacher` view
(`<snapshot_id>.html`; preview endpoint `?view=student|teacher`):
`lesson, worksheet, quiz, drill, recap, infographic, flashcard_deck, answer_key, roadmap` (9 × 2 views).

**B. Assessment exports** — wired inline (`_INLINE_ASSESSMENT_FORMATS`, export_writer.py:83),
derived from assessment artifacts (quiz/worksheet/drill):
- `gift` → `<run_id>.gift.txt` (Moodle GIFT; question kinds: multiple_choice_single/_multiple,
  true_false_4item, short_answer, cloze, matching, essay — `gift-impl/index.ts`)
- `h5p` → `<run_id>.h5p` (content types: multi-choice, true-false, blanks, summary, flashcards)
- `qti` → `<run_id>.qti.xml`

**C. Flashcard exports** — wired via Node CLI (`_SUBPROCESS_EXPORT_FORMATS`, :84), from `flashcard_deck`:
- `flashcard_tsv` (Quizlet/Anki TSV), `anki_apkg` (Anki .apkg SQLite deck)

**D. `google_forms`** — present in the `ExportFormat` literal but **NOT produced** by the gateway
writer (absent from both inline and subprocess sets) and requires Google OAuth + network
(`google-forms/client.ts` → `forms.googleapis.com`). **Deferred / out of offline e2e scope** —
covered by a dedicated issue (FFA-13), tested via a dry-run/mock, not in the offline full run.

**E. Pipeline modes** (`PipelineMode`, distinct output shapes / gates):
- `generate_pack` (default full pack)
- `diagnose_then_generate` (requires `student_evidence`; diagnostic + adapted pack)
- `plan_unit` (unit of lessons; opens `unit_approval` gate; roadmap output)
- `vocabulary_batch` (vocab clusters; own export: html/gift/h5p + manifest — `vocabulary-batch/index.ts`)

**F. Teacher scenarios** (decision paths, orthogonal to A–E):
manual approve · fast-lane auto-approve · scoped reject→regenerate · escalate ("Needs your review").

## Decision

1. **The full driver (FFA-10) MUST cover A + B + C across the four F scenarios**, requesting all
   9 artifact types and export_formats `[html, gift, h5p, qti, flashcard_tsv, anki_apkg]`, and
   emit every produced file (HTML student+teacher per artifact, plus each export) into the
   per-scenario output folder with an index.
2. **Each pipeline mode (E) is exercised at least once** (its own scenario entry), since modes
   produce different artifacts/gates (`plan_unit`→unit_approval + roadmap; `vocabulary_batch`→
   cluster manifest; `diagnose_then_generate`→diagnostic).
3. **`google_forms` (D) is explicitly deferred** with a documented reason (OAuth/network,
   unwired in gateway) and a separate dry-run test (FFA-13) — never silently dropped.
4. **Content coverage for assessment exports**: the driver's quiz/worksheet/drill requests must
   produce the question kinds GIFT/H5P/QTI support, so the exports are non-trivially exercised
   (not empty files). Assert each export file is non-empty and structurally valid.
5. **`summary.json` records the matrix coverage** — a checklist of (artifact_type × view) and
   (export_format) actually produced per scenario/mode, so a gap is visible, not silent
   (no-silent-truncation principle).

## Consequences

- The e2e run becomes a genuine full-coverage test: any regression that drops an artifact type,
  a view, an export format, or a mode surfaces as a missing matrix cell in `summary.json`.
- Assessment exports (gift/h5p/qti) — already wired but currently unexercised end-to-end — gain
  real coverage (FFA-12).
- `google_forms` scope is decided and documented rather than ambiguously "supported".
- Larger/slower e2e (many artifacts × formats × modes × scenarios, real LLM) → the driver must
  support a fixture-LLM fast mode for CI (FFA-10) while real-LLM remains the truth run.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Explicit full matrix incl. modes + assessment exports (chosen)** | True full test; gaps visible | Larger/slower run; needs fixture mode for CI |
| HTML + flashcards only | Fast | Misses gift/h5p/qti + modes — not a "full" test |
| Per-format unit tests only, no e2e matrix | Isolated | Doesn't prove the full pipeline produces every output together |
