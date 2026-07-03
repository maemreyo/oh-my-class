# [FFA-08] Implement ADR-024 flashcard exports (`flashcard_tsv` / `anki_apkg`)

Status: DONE
Labels: full-flow-api, exporters
ADR: 030, 024
Depends on: FFA-06

## Context

`flashcard_tsv` and `anki_apkg` are in `ExportFormat` + `SUPPORTED_EXPORTS`, and the writer
shells out to the Node CLI `packages/exporters/dist/cli.js` (built), but the flashcard export
path is only "Proposed" (ADR-024). Without a `flashcard_deck` artifact (FFA-06) these exports
have no content; with it, the wiring must be finished and ADR-024 accepted.

## Scope

- [x] Move ADR-024 status Proposed → Accepted; reconcile with ADR-030.
- [x] Wire export: when `export_formats` includes `flashcard_tsv`/`anki_apkg` AND a
      `flashcard_deck` artifact exists, produce those files via the Node CLI
      (`teaching_pack_export_writer.py` `_node_export`).
- [x] Fail-closed with a clear error if `packages/exporters/dist/cli.js` is not built;
      add the build step to CI/setup docs.
- [x] E2E: exported `.tsv` / `.apkg` land in `.scratch/pipeline-v2/artifacts/exports/<run_id>/`.

## Acceptance

- A run requesting `flashcard_deck` + `export_formats: [html, flashcard_tsv, anki_apkg]`
  produces valid HTML + TSV + APKG files; contents match the deck.
- Missing CLI → explicit fail-closed error (test), never a silent skip.

## References

- ADR-024, ADR-030. `teaching_pack_export_writer.py` (base_dir, `_node_export`),
  `packages/exporters/dist/cli.js`. Depends on FFA-06 (flashcard_deck generation).
