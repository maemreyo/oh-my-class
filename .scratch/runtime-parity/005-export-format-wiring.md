---
title: Wire the multi-format exporters into the teaching-pack export stage
status: done
labels: []
created: 2026-06-30
---

## What to build

Close the export cliff: `RunContract.export_formats` advertises `html, gift, h5p, qti, google_forms` and the exporters exist (`packages/exporters/src/{gift,h5p,qti,google-forms,anki-apkg,flashcard-tsv}`), but the teaching-pack `export_finalize` stage (`packages/agents/teaching_pack/nodes.py:213`) only ever emits `.html`. A teacher who requests GIFT/H5P/QTI silently gets only HTML.

- Implement an `ExporterRegistry` (or port) keyed by `ExportFormat`, mapping each format to its exporter module; HTML is always produced.
- Wire it into `export_finalize`: for each requested `export_format`, invoke the matching exporter over the approved artifacts and record the produced files in `exported_files`.
- **Fail-closed**: if a requested format has no registered exporter, raise/escalate — never silently substitute HTML.
- Keep the registry standalone and testable (artifact + format → file), reused by the topic-decomposition `UnitPackager` (topic-decomposition issue 017) for per-session export.

## Acceptance criteria

- [x] `ExporterRegistry` maps every `ExportFormat` value to an exporter; HTML is always emitted.
- [x] `export_finalize` produces a file per requested format and records them in `exported_files` (not just HTML).
- [x] A requested format with no exporter fails closed (clear error/escalation), never a silent HTML substitute.
- [x] The registry is standalone and reused by `UnitPackager` (topic-decomposition issue 017).
- [x] `ExportFormat` and the registry stay in sync (a test asserts every enum value has an exporter or is explicitly unsupported).

## Detailed test suite

(Real exporters + real rendered artifacts.)

- [x] `packages/agents/tests/teaching_pack/test_export_format_wiring.py`: requesting `["html","gift","qti"]` produces files of the correct formats.
- [x] same file: requesting a format with no exporter fails closed (no silent HTML-only result).
- [x] Sync test: every `ExportFormat` enum value resolves in the `ExporterRegistry` (or is explicitly marked unsupported).
- [x] Regression: an HTML-only request behaves as before.
- [x] Run `uv run pytest packages/agents/tests/teaching_pack/test_export_format_wiring.py -v`.

## Blocked by

None - can start immediately
