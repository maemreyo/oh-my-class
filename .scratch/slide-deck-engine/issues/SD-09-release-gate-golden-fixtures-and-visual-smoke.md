---
title: Prove slide_deck release readiness with golden fixtures and visual smoke
status: done
labels: [slide-deck-engine, testing, visual-qa, done]
created: 2026-07-06
---

## Parent

ADR-042 and ADR-031.

## What to build

Create the release evidence suite for native `slide_deck`. This is the final gate issue: it should prove that contracts, engine, pipeline integration, renderer surfaces, quality gates, teacher preview, scoped regeneration, export, and browser behavior work together.

The suite should use golden fixture decks and at least one integration scenario that exercises the teaching-pack pipeline with `lesson`, `slide_deck`, and an assessment artifact. It should cover student/teacher/print surfaces, answer-leak regressions, offline media, online-media warning/fallback behavior, scoped regeneration, and visual browser smoke.

## Acceptance criteria

- [x] Golden fixture decks cover: simple lesson deck, media-heavy deck, interaction deck, teacher-notes deck, and answer-leak regression deck.
- [x] Contract, engine, renderer, quality, gateway/export, and frontend tests for `slide_deck` pass in the normal test commands.
- [x] A full pipeline integration test produces a `slide_deck` artifact, teacher approval payload, and exported HTML.
- [x] Student-facing HTML is checked for absence of answer keys, correct answers, teacher notes, hidden answer JSON, external assets in offline mode, and raw provider/debug traces.
- [x] Playwright visual smoke runs at 375, 768, 1280, and 1920 px and covers slide navigation, reveal fallback, focus visibility, no horizontal overflow, dark mode, and print surface.
- [x] The output matrix records `slide_deck` student, teacher, and print HTML as covered outputs.
- [x] Manual QA runbook documents the exact browser/API/CLI surfaces used to verify the artifact end-to-end.

## Todo items

- [x] Add golden fixtures for simple lesson, media-heavy, interaction, teacher-notes, and answer-leak regression decks.
- [x] Run contract, engine, renderer, quality, gateway/export, and frontend slide-deck test suites.
- [x] Add full pipeline integration coverage for `slide_deck` artifact, teacher approval payload, and exported HTML.
- [x] Add student-facing HTML leak checks for answers, teacher notes, hidden JSON, external assets, and debug traces.
- [x] Add Playwright visual smoke for 375, 768, 1280, and 1920 px with navigation, reveal, focus, overflow, dark mode, and print coverage.
- [x] Update the output matrix and manual QA runbook with slide-deck surfaces and verification steps.

## Completion notes

- Added five golden deck fixtures under `.scratch/slide-deck-engine/fixtures/golden/`: simple lesson, media-heavy, interaction, teacher-notes, and answer-leak regression.
- Added contract fixture validation, renderer release-gate coverage for student/teacher/print output matrix, and Playwright visual smoke for 375/768/1280/1920 px.
- Added pipeline/export release coverage proving `lesson`, `slide_deck`, and `quiz` artifacts produce quality snapshots and approved HTML/export files together.
- Hardened `packages/agents/teaching_pack/quality.py` so slide-deck answer-key prechecks inspect student-facing slide content while ignoring canonical `teacher_notes` and `teacher_only` data that is removed by projection.
- Updated ADR-031 and the testbook runbook with `slide_deck:student`, `slide_deck:teacher`, and `slide_deck:print` output matrix cells and the exact release-gate commands.
- Verified with `uv run pytest common/contracts/tests/test_slide_deck_golden_fixtures.py packages/agents/tests/teaching_pack/test_slide_deck_release_gate.py services/gateway/tests/test_teaching_pack_export_writer.py -q` → `5 passed`.
- Verified with `pnpm --dir packages/renderer exec vitest run __tests__/slide-deck-renderer.test.ts __tests__/slide-deck-release-gate.test.ts` → `10 passed`.
- Verified browser visual smoke with `pnpm --dir apps/web exec playwright test tests/e2e/slide-deck-visual-smoke.spec.ts --reporter=list` → `12 passed` across 375, 768, 1280, and 1920 px.
- Verified `pnpm --dir apps/web typecheck` passed and LSP diagnostics were clean on changed Python/TypeScript files. Renderer tests still emit the existing sanitizer warning for allowing `<style>` in standalone HTML sanitization.

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
