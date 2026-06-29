---
title: Review Present Tenses pack end to end after provenance and polish
status: completed-with-gaps
labels: [ready-for-agent, teaching-pack, present-tenses, review]
created: 2026-06-29
order: 5
blocked_by: [ISSUE-002-present-tenses-quality-gate-evidence, ISSUE-004-polish-present-tenses-html-uiux]
---

## What to build

Perform the final end-to-end review of the Present Tenses Teaching Pack after it has real system provenance, quality evidence, improved inverse-thinking scaffolding, and UI/UX polish. The output should be a clear go/no-go verdict for classroom use and for demonstrating system capability.

## Acceptance criteria

- [ ] Review confirms whether the final pack is system-generated, scratch-authored, or mixed, with evidence paths.
- [ ] Review checks pedagogy, grammar accuracy, inverse-thinking depth, UI/UX, responsive rendering, and hard invariants.
- [ ] Review identifies any remaining blockers separately from nice-to-have improvements.
- [ ] Review includes the final browser artifact path and screenshots.
- [ ] Review states whether the pack is ready to use with students.

## Blocked by

- ISSUE-002-present-tenses-quality-gate-evidence
- ISSUE-004-polish-present-tenses-html-uiux

## Current review state

- The pack has a completed active run and deterministic invariant evidence.
- The prior student-preview/output path was too lossy for a polished classroom-use verdict; that gateway seam is now fixed for new snapshots.
- The current completed run still lacks browser screenshot evidence and LLM judge/provider attribution. Final review must stay `in-progress` until those are either produced or explicitly accepted as gaps.
- Fresh post-fix run `cf1bf05f-dbf5-48bd-858a-2956c59dbb49` now has browser screenshots and deterministic layout checks.
- Final review remains in progress because ISSUE-003 pedagogy criteria are not fully met and Layer 4/Layer 6 judge/provider attribution remains absent.

## Final review evidence

- Final post-prompt-fix completed run: `57561ab4-d813-4ccd-be8d-f402a7f557c7`.
- Evidence file: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe-final.json`.
- Pedagogy matrix: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-final-pedagogy-check.json`.
- Student preview artifact paths:
  - `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-5497cd94edbccd47144889d5-student.html`
  - `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-b30485b1b8485191f66d2b3c-student.html`
  - `.scratch/teaching-pack-present-tenses/artifacts/live-exports/57561ab4-d813-4ccd-be8d-f402a7f557c7/snap-c450c5413ad4af80f94a589b-student.html`
- Final run checks:
  - System-generated through active `/teaching-packs/*`, not scratch-authored HTML.
  - Contract gate and content approval gate were both responded to.
  - `ArtifactContent` validation passed for lesson, worksheet, and quiz.
  - Preview invariants passed: doctype, brand, no external URLs, and no student-visible answer-key markers.
  - Inverse-thinking pedagogy criteria now pass for exit ticket, `wrong_reasons`, stative transfer examples, and “listener wrongly hears” language.

## Final remaining gaps

- Final run evidence did not report release export paths (`export_paths: []`), so the validated student preview HTML is the usable final surface for this review.
- Final run still lacks a worked homework video model in the generated payload.
- Completed runs still have no per-provider evidence and no Layer 4/Layer 6 multi-judge records, so the review cannot claim provider-level or judge-layer provenance.

## Verdict

The pack is ready as a system-generated preview/demo teaching pack and is usable with teacher review for the lesson/worksheet/quiz flow. For a strict classroom-release claim, follow up on the missing homework-video model and missing provider/judge-layer evidence.
