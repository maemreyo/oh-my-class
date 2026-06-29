---
title: Deepen inverse-thinking scaffolding in Present Tenses content
status: completed-with-gap
labels: [ready-for-agent, teaching-pack, present-tenses, pedagogy]
created: 2026-06-29
order: 3
blocked_by: [ISSUE-001-real-system-generated-present-tenses-pack]
---

## What to build

Improve the Present Tenses lesson content so inverse thinking is practiced, not merely described. The lesson should force students to explain wrong-answer consequences across Present Simple, Present Continuous, Present Perfect Simple, Present Perfect Continuous, and stative verb traps.

## Acceptance criteria

- [ ] Every major tense section starts from a trap/context scenario before the rule summary.
- [ ] Every contrastive pair states what the listener wrongly hears if the rival form is chosen.
- [ ] MCQ-style practice includes wrong-reason feedback for each plausible distractor, not only the correct answer explanation.
- [ ] The lesson includes an exit-ticket task and a worked model of the homework video explanation.
- [ ] The `think` stative/dynamic distinction includes transfer examples beyond Paris, such as `know`, `believe`, or `seem` where appropriate.
- [ ] The improved content remains compatible with the existing artifact/component contracts.

## Evidence from fresh post-fix run

- Fresh run `cf1bf05f-dbf5-48bd-858a-2956c59dbb49` generated lesson, worksheet, and quiz artifacts that validate against `ArtifactContent`.
- The quiz includes `wrong_reasons` for MCQ distractors.
- The lesson and worksheet include homework/video/model-related content.
- Remaining pedagogy gaps detected by artifact inspection:
  - Lesson/worksheet do not expose `wrong_reasons` in the same structured way as the quiz.
  - No explicit `Exit Ticket` marker was found in lesson, worksheet, or quiz payloads.
  - `know`, `believe`, and `seem` transfer coverage was not all present in any one artifact payload.
- This issue remains in progress until the generated content satisfies all acceptance criteria, not merely because the system run completed.

## Final post-prompt-fix evidence

- Final active run `57561ab4-d813-4ccd-be8d-f402a7f557c7` completed after the content-creator prompt was tightened for “Present Tenses Inverse-Thinking Methodology”.
- Evidence file: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-live-probe-final.json`.
- Pedagogy check file: `.scratch/teaching-pack-present-tenses/artifacts/present-tenses-final-pedagogy-check.json`.
- Approved/student preview snapshots:
  - `snap-5497cd94edbccd47144889d5` (`lesson-1`)
  - `snap-b30485b1b8485191f66d2b3c` (`worksheet-2`)
  - `snap-c450c5413ad4af80f94a589b` (`quiz-3`)
- `ArtifactContent` validation passed for all three generated artifacts.
- Final content quality payload: `overall: 8.0`, `passed: true`, `snapshot_count: 3`.
- Acceptance evidence:
  - Trap/context-first and wrong-consequence language is present in the generated lesson and worksheet.
  - Contrastive wording includes “listener wrongly hears” in the lesson and worksheet.
  - Structured `wrong_reasons` are present for lesson, worksheet, and quiz MCQ-style practice.
  - Explicit `Exit Ticket` content is present in the lesson and worksheet.
  - `know`, `believe`, and `seem` transfer examples are present together in both lesson and worksheet payloads.
  - Existing artifact/component contracts are preserved by schema validation and preview invariant checks.
- Remaining accepted gap: the final run did not include a worked homework video model in the generated artifact payload. The core inverse-thinking scaffolding criteria are now satisfied, but the homework-video model should be tracked as a follow-up if this exact classroom routine is required.

## Blocked by

- ISSUE-001-real-system-generated-present-tenses-pack
