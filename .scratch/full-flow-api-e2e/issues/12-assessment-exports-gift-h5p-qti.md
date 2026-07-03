# [FFA-12] Assessment export coverage — gift / h5p / qti

Status: TODO
Labels: full-flow-api, exporters, e2e
ADR: 031, 030
Depends on: FFA-06/07 (artifacts), FFA-10 (driver)

## Context

`gift`, `h5p`, `qti` are wired inline in the gateway export writer
(`_INLINE_ASSESSMENT_FORMATS`, `services/gateway/teaching_pack_export_writer.py:83`) and
implemented in `packages/exporters/src/{gift,h5p,qti}` (GIFT supports MC single/multiple,
true_false_4item, short_answer, cloze, matching, essay; H5P has multi-choice, true-false,
blanks, summary, flashcards content types). They derive from assessment artifacts
(quiz/worksheet/drill) but are currently **unexercised end-to-end** — no driver requests them.

## Scope

- [ ] Driver requests `export_formats` including `gift, h5p, qti` for a run with
      quiz/worksheet/drill artifacts.
- [ ] Ensure the generated assessment content includes the question kinds GIFT/H5P/QTI support
      so exports are non-trivial (not empty).
- [ ] Assert each produced file (`<run_id>.gift.txt`, `.h5p`, `.qti.xml`) exists, is non-empty,
      and is structurally valid (GIFT parses; .h5p is a valid zip with content.json; QTI is
      well-formed XML).
- [ ] Include these files in the per-scenario output folder + `summary.json` matrix.

## Acceptance

- A full run emits valid gift/h5p/qti files with real question content; validated in the e2e.
- `summary.json` shows gift/h5p/qti as produced (matrix cells filled).

## References

- ADR-031, ADR-030. `teaching_pack_export_writer.py:59-61,83,131-142`,
  `packages/exporters/src/{gift-impl,h5p-impl,qti}`.
