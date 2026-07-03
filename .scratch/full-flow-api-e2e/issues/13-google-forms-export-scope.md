# [FFA-13] google_forms export — decide scope + dry-run coverage

Status: DONE
Labels: full-flow-api, exporters
ADR: 031
Depends on: none

## Context

`google_forms` is in the `ExportFormat` literal and `_export_format` maps to it
(`teaching_pack_export_writer.py:125-128`), but it is **not** in `_INLINE_ASSESSMENT_FORMATS`
nor `_SUBPROCESS_EXPORT_FORMATS`, so the gateway writer never actually produces it. The
implementation (`packages/exporters/src/google-forms/`) requires Google OAuth + live network
(`forms.googleapis.com`). It cannot run in an offline/CI full test.

## Scope

- [x] Decide + document status: either (a) explicitly **out of offline e2e scope** (deferred,
      with reason), or (b) wire it behind credentials with a dry-run/mock path.
- [x] If kept: add a mock/dry-run test (question_mapper output validated without network) so the
      mapping logic is covered; mark the live path as manual/credentialed-only.
- [x] If deferred: remove `google_forms` from advertised/requestable export_formats OR clearly
      document it as unsupported so requesting it fails fast instead of silently producing nothing.
- [x] Reflect the decision in ADR-031's matrix (D).

## Acceptance

- No silent gap: requesting `google_forms` either produces output (dry-run/mock verified) or
  fails fast with a clear "unsupported/credentialed-only" error — never a silent no-op.
- ADR-031 matrix updated with the final status.

## References

- ADR-031 (matrix D). `teaching_pack_export_writer.py:125-128`,
  `packages/exporters/src/google-forms/{client,auth,question-mapper}.ts`.
