---
title: Why Wrong Reasoning mode UI polish and R5 visibility
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Polish `why_wrong_reasoning` as a first-class diagnostic mode. The existing R5 quality rule requires every `question_card` to contain non-empty `wrong_reasons`, but there is no clear teacher-facing inspector/editor affordance for those reasons. This issue makes the reasoning visible, editable, and testable without leaking answers to students.

## Acceptance criteria

- [ ] Teacher inspector shows per-question wrong-reason coverage and flags missing options.
- [ ] Structured editor lets teachers edit wrong reasons per distractor/choice.
- [ ] Student-facing UI reveals wrong reasoning only at the intended time/surface, not as hidden scrapeable answer-key content.
- [ ] Quality gate R5 messages link to the relevant question card in the editor.
- [ ] Renderer has a dedicated partial or clear component section for wrong-reason explanation.

## Detailed test suite

- [ ] `packages/quality` R5 test: Given `why_wrong_reasoning` and a question card missing `wrong_reasons`, when gate runs, then it fails with question ID and missing option context.
- [ ] Renderer test: Given wrong reasons, when initial student HTML renders, then reasons are not visible unless the artifact type intentionally supports reveal feedback.
- [ ] Renderer test: Given teacher output, when rendered, then wrong reasons are grouped by question and distractor.
- [ ] UI editor test: Given a question card, when a teacher edits a distractor reason, then schema validation runs and quality status updates.
- [ ] Inspector deep-link test: Given an R5 violation, when the teacher clicks it, then focus moves to the offending question card field.
- [ ] Accessibility test: Wrong-reason feedback is announced after selection/reveal and does not rely on color alone.

## Blocked by

- .scratch/inverse-thinking/008-system-wide-mode-ui-polish.md
