---
title: Wire anki-apkg and flashcard-tsv into Python export pipeline
status: done
labels: [export, anki, flashcard, python-ts-bridge]
created: 2026-07-01
---

## What to build

`packages/exporters/src/anki-apkg/` and `packages/exporters/src/flashcard-tsv/` are **fully functional TS exporters** (verified in `packages/exporters/src/`). They are **not in the Python `ExportFormat` type or `ExporterRegistry`** at all — no Python caller invokes them.

The TS exporter pattern already exists: `packages/renderer/` is called via Node subprocess (JSON via stdin → output via stdout), wired in `services/gateway/renderer_adapter.py`. Apply the same pattern for anki and flashcard-tsv.

**What to change:**

1. **`common/contracts/run_contract.py`**: Add `"anki_apkg"` and `"flashcard_tsv"` to `ExportFormat` `Literal` type.
2. **`packages/agents/teaching_pack/exporters.py`**: Add `ExportFormat` literals, add entries to `_SUPPORTED_FORMATS`, implement `export()` branches that call the TS exporters via Node subprocess (following `renderer_adapter.py` pattern — JSON in, output path out, timeout, fail-closed).
3. **Node subprocess bridge**: Create `packages/exporters/dist/` build step (add to `pnpm` workspace/Turborepo). The bridge entrypoint receives `{format, run_id, artifacts}` via stdin, routes to the appropriate exporter, writes the output file, returns the path via stdout.
4. **Schema parity**: regenerate Zod and FE transport types to include new `ExportFormat` values.
5. **Manifest sync**: re-run `scripts/generate_architecture_manifest.py`; `architecture.manifest.json::export_formats.supported` should now include `anki_apkg` and `flashcard_tsv`.

**Scope boundaries:**
- `google_forms` stays in `_UNSUPPORTED_FORMATS` — it needs OAuth credential setup (separate issue).
- Anki exporter produces `.apkg` binary; flashcard-tsv produces a `.tsv`. Both should be stored in `exports/{run_id}/` via `teaching_pack_export_writer.py`.

## Acceptance criteria

- [ ] `ExportFormat` contract includes `"anki_apkg"` and `"flashcard_tsv"`.
- [ ] `ExporterRegistry.supports("anki_apkg")` and `ExporterRegistry.supports("flashcard_tsv")` both return `True`.
- [ ] A run requesting `export_format="anki_apkg"` produces a `.apkg` file in `exports/{run_id}/`.
- [ ] A run requesting `export_format="flashcard_tsv"` produces a `.tsv` file in `exports/{run_id}/`.
- [ ] Node subprocess bridge is fail-closed: error/timeout → `ExportError`, never silently falls back to HTML.
- [ ] `architecture.manifest.json::export_formats.supported` includes `anki_apkg` and `flashcard_tsv` (CI drift test passes).

## Detailed test suite

(Real DB + real LLM via 9router port 20228, model `4omc`.)

- [ ] `packages/agents/tests/teaching_pack/test_anki_export.py`: mock a completed `TeachingPackState` with a quiz artifact → request `anki_apkg` export → verify `.apkg` file exists and is non-empty. (Subprocess can be mocked if TS build is unavailable in CI.)
- [ ] Same for `flashcard_tsv` → `.tsv` with correct column headers.
- [ ] Fail-closed: exporter raises `ExportError` when Node subprocess exits non-zero.
- [ ] Manifest sync: `python scripts/generate_architecture_manifest.py` and the resulting `architecture.manifest.json` includes `anki_apkg` and `flashcard_tsv` in `export_formats.supported`.
- [ ] `tests/test_architecture_sync.py` passes with the new formats.

## Blocked by

- parity-005 (done ✅) — ExporterRegistry pattern established
