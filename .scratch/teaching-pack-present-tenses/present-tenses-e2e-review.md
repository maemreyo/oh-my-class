# Present Tenses Teaching Pack E2E Review

## Verdict

Status: **completed with explicit gaps; usable for preview/demo and teacher-reviewed classroom use**.

The Present Tenses pack now has a real active `/teaching-packs/*` completed run after the preview-rendering fix and after the Present Tenses inverse-thinking prompt hardening. It has deterministic invariant evidence, contract validation, final pedagogy checks, and browser screenshots from the previous post-preview-fix export. The result is usable as a generated teaching-pack preview/demo and can be used with teacher review. Strict classroom-release evidence still has explicit gaps: no homework-video model, no provider-level attribution, and no Layer 4/Layer 6 multi-judge records.

## Provenance

- Completed run: `ac6872bd-32c5-4cf0-a5bd-86c15e717723`.
- Evidence: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-completed-run-evidence.json`.
- Fresh post-fix completed run: `cf1bf05f-dbf5-48bd-858a-2956c59dbb49`.
- Fresh post-fix evidence: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe.json`.
- Final post-prompt-fix completed run: `57561ab4-d813-4ccd-be8d-f402a7f557c7`.
- Final run evidence: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe-final.json`.
- Final pedagogy matrix: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-final-pedagogy-check.json`.
- Gate/event evidence includes:
  - `teaching_pack.contract_confirmation.opened`
  - `teaching_pack.content_approval.opened`
  - `teaching_pack.content.approved_snapshots`
  - `teaching_pack.run.completed`
- Approved snapshots:
  - `snap-779fa941949414ec6811cb23`
  - `snap-570b73ea2e3564d33ea4e668`
  - `snap-bdd09f198501fa6e81153d48`
- Fresh post-fix approved snapshots:
  - `snap-df36108befb2f3bd178c33a5` (`lesson-1`)
  - `snap-40fa97c7f356893ff64f5491` (`worksheet-2`)
  - `snap-d481d39aae76b35a2c63c76e` (`quiz-3`)
- Final post-prompt-fix approved snapshots:
  - `snap-5497cd94edbccd47144889d5` (`lesson-1`)
  - `snap-b30485b1b8485191f66d2b3c` (`worksheet-2`)
  - `snap-c450c5413ad4af80f94a589b` (`quiz-3`)

## Deterministic quality evidence

All three captured student preview copies passed these checks:

- `<!DOCTYPE html>` present.
- `oh-my-class` brand present.
- No `http://` or `https://` asset references.
- No student-visible answer-key markers detected.

Fresh post-fix exported HTML checks also passed for all three exports: `doctype=true`, `brand=true`, `external_urls=false`, `answer_markers=false`, and `viewport_meta=true`.

Fresh post-fix artifact contract validation passed with `ArtifactContent`:

- `lesson-1`: 9 sections.
- `worksheet-2`: 6 sections.
- `quiz-3`: 8 sections.

The fresh `content_approval` quality payload recorded `overall: 8.0`, `passed: true`, `snapshot_count: 3`.

Final post-prompt-fix artifact contract validation passed with `ArtifactContent`:

- `lesson-1`: 8 sections.
- `worksheet-2`: 7 sections.
- `quiz-3`: 2 sections.

The final `content_approval` quality payload recorded `overall: 8.0`, `passed: true`, `snapshot_count: 3`.

Final student preview paths:

- `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-5497cd94edbccd47144889d5-student.html`
- `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-b30485b1b8485191f66d2b3c-student.html`
- `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-c450c5413ad4af80f94a589b-student.html`

Final run caveat: `export_paths` was empty in release evidence, so the final validated student previews are the usable reviewed surface.

## Rendering fix completed

Root issue found: `TeachingPackSnapshotStore.create_snapshot()` generated `student_rendered_html` from `content_json` when a caller did not provide a student-specific HTML version. That path flattened rich rendered components into primitive text-only `<section>` blocks.

Fix: new snapshots now default `student_rendered_html` to `payload.rendered_html`, then run `remove_answer_keys_from_html()` so the public student preview preserves renderer markup while removing teacher-only sections.

Regression evidence:

- `services/gateway/tests/test_teaching_pack_previews.py::TestTeachingPackPreviews::test_student_preview_preserves_rendered_snapshot_markup` fails on the old behavior and passes after the fix.
- Focused preview tests: `8 passed`.
- Route probe for a fresh snapshot returned status `200`, preserved `class="lesson-card"` and `Inverse-thinking trap`, and removed `Answer Key`/`Correct answer`.

## Browser QA

Generated lesson export opened through a temporary localhost static server:

- HTML path: `.scratch/pipeline-v2/artifacts/exports/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/snap-df36108befb2f3bd178c33a5.html`.
- Desktop screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-desktop-1280.png`.
- Mobile screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/cf1bf05f-dbf5-48bd-858a-2956c59dbb49/lesson-mobile-375.png`.

Objective Playwright layout checks:

- Desktop `1280x900`: no horizontal overflow; 1 H1, 17 H2, 1 H3, 7 sections, 2 tables; tables fit inside viewport.
- Mobile `375x812`: no horizontal overflow; tables fit at `339px` inside `375px` viewport.
- Console: one non-content 404 for `/favicon.ico` from the temporary static server; no pack script/runtime error observed.

Final post-prompt-fix lesson preview also opened through a temporary localhost static server:

- HTML path: `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-5497cd94edbccd47144889d5-student.html`.
- Desktop screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/57561ab4-d813-4ccd-be8d-f402a7f557c7/lesson-desktop-1280.png`.
- Mobile screenshot: `.scratch/teaching-pack-present-tenses/artifacts/browser-qa/57561ab4-d813-4ccd-be8d-f402a7f557c7/lesson-mobile-375.png`.

Final objective Playwright layout checks:

- Desktop `1280x900`: no horizontal overflow; 1 H1, 7 sections, 0 tables; `Exit Ticket`, “listener wrongly hears”, and `oh-my-class` brand present; no answer-key marker detected.
- Mobile `375x812`: no horizontal overflow; 1 H1, 7 sections, 0 tables; `Exit Ticket`, “listener wrongly hears”, and `oh-my-class` brand present; no answer-key marker detected.
- Console: one non-content 404 for `/favicon.ico` from the temporary static server; no pack script/runtime error observed.

## Pedagogy review

The final post-prompt-fix run satisfies the core inverse-thinking scaffolding criteria that were missing in the earlier completed run:

- Explicit `Exit Ticket` content appears in the lesson and worksheet.
- Structured `wrong_reasons` appear in lesson, worksheet, and quiz practice.
- `know`, `believe`, and `seem` stative-transfer examples appear together in both lesson and worksheet payloads.
- “Listener wrongly hears” contrastive language appears in the lesson and worksheet.
- The generated artifacts remain compatible with the existing `ArtifactContent` contract.

Remaining pedagogy gap: the final generated payload still does not include a worked homework video model.

## Remaining gaps

1. Homework-video model remains absent from the final generated payload.
2. The completed runs have `artifact_ids: []` and `provider_evidence: []`, so they prove active lifecycle/snapshot/export behavior but not per-provider LLM attribution.
3. No Layer 4 or Layer 6 judge records exist for these Present Tenses runs.
4. Final run release evidence did not report export paths; validated student preview HTML is the reviewed final surface.

## Next action

For stricter classroom-release evidence, add generation support for the homework-video model and wire provider/judge evidence into the active run evidence. No manual editing of generated HTML should be used to satisfy those gaps.
