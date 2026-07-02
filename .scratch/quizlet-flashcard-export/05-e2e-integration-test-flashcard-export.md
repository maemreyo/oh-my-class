---
title: "End-to-end integration test for flashcard export flow"
status: completed
labels: [testing, flashcard-export]
created: 2026-07-02
completed: 2026-07-02
adr: 024
---

## What to build

Create an end-to-end integration test that verifies the complete flashcard export flow: from Content Creator Agent output to final TSV/APKG files.

This test validates the full vertical slice:
1. Content Creator Agent produces a `flashcard_deck` artifact
2. The artifact passes Pydantic validation
3. The `export_finalize` stage invokes the CLI bridge
4. The CLI bridge writes a valid `.tsv` file (Quizlet-compatible format)
5. The CLI bridge writes a valid `.apkg` file (Anki-compatible format)
6. The TSV content matches expected format: `front\tback\ttags` per line
7. The TSV content can be imported into Quizlet (format verification)

Key test files:
- `packages/agents/tests/teaching_pack/test_anki_export.py` — existing test patterns
- `packages/exporters/__tests__/flashcard-tsv.test.ts` — existing TSV exporter tests
- `packages/exporters/__tests__/anki-apkg.test.ts` — existing APKG exporter tests

## Acceptance criteria

- [x] Integration test: run with `export_formats: ["flashcard_tsv"]` produces a `.tsv` file
- [x] Integration test: run with `export_formats: ["anki_apkg"]` produces an `.apkg` file
- [x] Integration test: run with `export_formats: ["html", "flashcard_tsv"]` produces both file types
- [x] TSV content validation: each line has format `front\tback` or `front\tback\ttags`
- [x] TSV content validation: no empty lines, no placeholder text (`[TBD]`, `lorem ipsum`)
- [x] TSV content validation: Vietnamese diacritics render correctly in the output
- [x] APKG file validation: file is a valid ZIP with expected internal structure
- [x] Regression test: existing export formats (html, gift, h5p, qti) still work
- [x] Test covers the fallback path: quiz/drill Q&A pairs converted to flashcards when no flashcard_deck artifact exists

## Blocked by

- Issue #01 (flashcard_deck must be a valid artifact_type first)
- Issue #02 (subprocess exports must be wired first)
