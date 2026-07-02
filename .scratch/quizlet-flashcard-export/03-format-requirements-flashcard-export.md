---
title: "Add FORMAT_REQUIREMENTS for flashcard export formats"
status: completed
labels: [quality-gate, flashcard-export]
created: 2026-07-02
completed: 2026-07-02
adr: 024
---

## What to build

Add `flashcard_tsv` and `anki_apkg` to the `FORMAT_REQUIREMENTS` dict in `packages/quality/layer6_export/export_validator.py`. This ensures the Layer 6 quality gate validates that required artifact types exist before attempting export.

Currently, `FORMAT_REQUIREMENTS` only covers `html`, `gift`, `h5p`, and `qti`. The flashcard formats are not registered, so the quality gate cannot enforce that `flashcard_deck` artifacts exist when these formats are requested.

Key file: `packages/quality/layer6_export/export_validator.py` — `FORMAT_REQUIREMENTS` dict (lines 7-12)

## Acceptance criteria

- [x] `FORMAT_REQUIREMENTS["flashcard_tsv"]` specifies `flashcard_deck` as the required artifact type
- [x] `FORMAT_REQUIREMENTS["anki_apkg"]` specifies `flashcard_deck` as the required artifact type
- [x] When a run requests `flashcard_tsv` but no `flashcard_deck` artifact exists, the quality gate reports a readiness failure
- [x] When a run requests `flashcard_tsv` and a `flashcard_deck` artifact exists, the quality gate passes
- [x] Existing FORMAT_REQUIREMENTS for html/gift/h5p/qti are unchanged
- [x] Unit tests cover both pass and fail cases for flashcard format requirements

## Blocked by

- Issue #01 (flashcard_deck must be a valid artifact_type first)
