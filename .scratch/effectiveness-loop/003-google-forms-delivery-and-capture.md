---
title: Google Forms delivery + response capture (auto, no manual entry)
status: done
labels: []
created: 2026-06-30
---

## What to build

Auto-deliver assessments and auto-capture results with zero teacher data entry, riding the existing `packages/exporters/src/google-forms` exporter (already API-driven: OAuth + `createForm` + `batchUpdate` + per-type `question-mapper` with point values / TF-4-item). The system creates the whole form; the tutor just shares the link; results flow back automatically.

- **Delivery (forward)**: wire `google_forms` into the export/delivery flow (scaling-resilience 005). One action creates a Google Form quiz (all questions + correct answers + points, quiz-mode auto-grade) and returns `responderUri` (the share link). No question-by-question building.
- **Capture (reverse — new)**: add `forms.responses.list` to the Forms client; **poll** responses (per-delivery, scheduled or on "check results"); auto-grade by reading Forms' quiz scores for objective items + LLM-grade (9router) for essay/open; normalize to `StudentAttempt` (issue 001), mapped to KC via question `kc_ids`.
- **Pseudonymize on ingest**: map respondent → stable per-class pseudonym; do not store raw email/name in the outcome store.
- Print-pack stays offline/no-JS (invariant intact) — this is a parallel digital-delivery channel. (Push via Apps Script trigger and xAPI/Zalo are later channels.)

## Acceptance criteria

- [x] One delivery action creates a complete Google Form (all questions, correct answers, points) and returns the share link; no manual per-question building.
- [x] Responses are pulled via `forms.responses.list`; objective items use Forms' auto-grade, essay/open use the essay-grade seam.
- [x] Each response normalizes to a `StudentAttempt` mapped to KC via `kc_ids`, pseudonymized on ingest.
- [x] Capture requires consent (issue 001) and keeps Google Forms as a separate digital channel.
- [x] Print-pack output is unchanged (offline/no-JS); google_forms is a separate channel.

## Detailed test suite

(Real DB; Google Forms API against a test form/account or a recorded-contract double at the HTTP boundary; LLM grading via 9router.)

- [x] `packages/exporters/__tests__/google-forms.test.ts`: quiz creation plus response normalization, KC mapping, auto-grade, pseudonymization, and essay-score seam.
- [x] `services/gateway/tests/test_forms_response_capture.py`: pulled responses normalize to `StudentAttempt` with correct KC mapping and pseudonymization; objective scores match Forms auto-grade.
- [x] Consent refusal is covered in the gateway capture tests.
- [x] Essay-score seam test: an open response score is attached to the attempt.
- [x] Run `pnpm --filter @oh-my-class/exporters test -- google-forms.test.ts` and `uv run pytest services/gateway/tests/test_forms_response_capture.py -q`.

## Verification

- `pnpm --filter @oh-my-class/exporters test -- google-forms.test.ts` → 51 passed.
- `uv run pytest services/gateway/tests/test_forms_response_capture.py -q` → 2 passed.

## Blocked by

- .scratch/effectiveness-loop/001-outcome-model-and-privacy-foundation.md
- .scratch/runtime-parity/005-export-format-wiring.md  (✅ DONE — export/ExporterRegistry wiring)
