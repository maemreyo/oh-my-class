---
title: Prove slide_deck release readiness with golden fixtures and visual smoke
status: ready-for-agent
labels: [slide-deck-engine, testing, visual-qa, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-042 and ADR-031.

## What to build

Create the release evidence suite for native `slide_deck`. This is the final gate issue: it should prove that contracts, engine, pipeline integration, renderer surfaces, quality gates, teacher preview, scoped regeneration, export, and browser behavior work together.

The suite should use golden fixture decks and at least one integration scenario that exercises the teaching-pack pipeline with `lesson`, `slide_deck`, and an assessment artifact. It should cover student/teacher/print surfaces, answer-leak regressions, offline media, online-media warning/fallback behavior, scoped regeneration, and visual browser smoke.

## Acceptance criteria

- [ ] Golden fixture decks cover: simple lesson deck, media-heavy deck, interaction deck, teacher-notes deck, and answer-leak regression deck.
- [ ] Contract, engine, renderer, quality, gateway/export, and frontend tests for `slide_deck` pass in the normal test commands.
- [ ] A full pipeline integration test produces a `slide_deck` artifact, teacher approval payload, and exported HTML.
- [ ] Student-facing HTML is checked for absence of answer keys, correct answers, teacher notes, hidden answer JSON, external assets in offline mode, and raw provider/debug traces.
- [ ] Playwright visual smoke runs at 375, 768, 1280, and 1920 px and covers slide navigation, reveal fallback, focus visibility, no horizontal overflow, dark mode, and print surface.
- [ ] The output matrix records `slide_deck` student, teacher, and print HTML as covered outputs.
- [ ] Manual QA runbook documents the exact browser/API/CLI surfaces used to verify the artifact end-to-end.

## Blocked by

- SD-01 slide deck contracts and schema parity.
- SD-02 SlideDeckEngine skeleton and typed registries.
- SD-03 minimal slide_deck tracer through the teaching-pack pipeline.
- SD-04 slide surfaces and answer-leak-safe projection.
- SD-05 interaction modules and media policy.
- SD-06 engine quality, typed healing, scorecard, and observability.
- SD-07 scoped slide_deck regeneration from teacher feedback.
- SD-08 slide-native teacher preview UX inside the existing approval gate.

## References

- `docs/adr/031-full-output-test-matrix.md`
- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `docs/testbook/runbook.md`
- `tests/integration/`
- `tests/e2e/`
- `packages/renderer/__tests__/`
- `packages/quality/`

## Implementation notes

- Treat this as a release gate, not as a place to implement missing production behavior.
- If this issue finds missing behavior, open or return to the responsible earlier issue instead of weakening assertions.
- Browser visual smoke is required because slide usability cannot be proven by schema tests alone.
