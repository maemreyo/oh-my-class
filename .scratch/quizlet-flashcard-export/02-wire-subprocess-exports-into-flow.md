---
title: "Wire flashcard_tsv and anki_apkg into teaching-pack export flow"
status: completed
labels: [export, flashcard-export, pipeline]
created: 2026-07-02
completed: 2026-07-02
adr: 024
---

## What to build

Wire the existing `flashcard_tsv` and `anki_apkg` subprocess exporters into the teaching-pack pipeline's `export_finalize` stage.

Currently, `_export_finalize` in `packages/agents/teaching_pack/nodes.py` returns file paths for all formats, but the actual file writing for subprocess formats (`flashcard_tsv`, `anki_apkg`) happens via the CLI bridge (`packages/exporters/src/cli.ts`) invoked by the gateway-side `teaching_pack_export_writer.py`.

The agent-side `_export_finalize` needs to signal that subprocess formats require gateway-side execution. The gateway-side writer already handles `anki_apkg` and `flashcard_tsv` in `_SUBPROCESS_EXPORT_FORMATS`.

Key files:
- `packages/agents/teaching_pack/nodes.py` — `_export_finalize` function (line 476)
- `services/gateway/teaching_pack_export_writer.py` — `_SUBPROCESS_EXPORT_FORMATS`
- `packages/exporters/src/cli.ts` — CLI bridge that invokes `FlashcardTSVExporter` and `AnkiApkgExporter`

## Acceptance criteria

- [x] When `contract.export_formats` includes `"flashcard_tsv"`, the export writer invokes the CLI bridge with format=`flashcard_tsv`
- [x] When `contract.export_formats` includes `"anki_apkg"`, the export writer invokes the CLI bridge with format=`anki_apkg`
- [x] The CLI bridge receives `flashcard_deck` artifacts (or falls back to quiz/drill Q&A pairs)
- [x] Output files are written to `exports/{run_id}/{run_id}.tsv` and `exports/{run_id}/{run_id}.apkg`
- [x] Existing export formats (html, gift, h5p, qti) continue to work with zero regression
- [x] Integration test: a run with `export_formats: ["html", "flashcard_tsv"]` produces both `.html` and `.tsv` files

## Blocked by

- Issue #01 (flashcard_deck must be a valid artifact_type first)
