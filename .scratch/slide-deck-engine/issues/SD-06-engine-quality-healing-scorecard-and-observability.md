---
title: Add engine quality, typed healing, scorecard, and observability
status: done
labels: [slide-deck-engine, quality, observability, done]
created: 2026-07-06
---

## Parent

ADR-040 and ADR-042.

## What to build

Make `SlideDeckEngine` self-auditing before the existing pack-level judge runs. The engine should produce typed validation failures, scoped healing attempts, deterministic quality scorecards, and redacted trace artifacts so developers and teachers can understand why a deck was produced or repaired.

The deterministic scorecard should cover objective coverage, pacing fit, text density, visual variety, accessibility completeness, interaction appropriateness, teacher-only separation, offline readiness, and source-reference coverage. Healing should repair the narrowest safe scope: block, slide, plan, or whole deck.

## Acceptance criteria

- [x] Engine validators return typed failure codes for density overflow, invalid layout/block/interaction, missing alt text, unsupported media, pacing mismatch, missing source refs, teacher-only leak risk, and objective coverage gaps.
- [x] Healing maps each failure class to a scoped repair strategy and records attempts, outcomes, and final status.
- [x] Deterministic scorecard is produced for every generated deck and is testable without LLM judge calls.
- [x] Engine trace artifacts include plan, data, validation report, healing report, scorecard, source-ref map, model/cost metadata placeholders, and export readiness manifest.
- [x] Trace artifacts are internal only and redact or omit student PII, raw untrusted research prose where inappropriate, answer keys from student-surface diagnostics, and provider stack traces.
- [x] Existing Layer 4 judge remains the qualitative gate; deterministic scorecard does not replace it.

## Todo items

- [x] Define typed slide-deck validation failure codes and validator outputs.
- [x] Map each failure class to block, slide, plan, or deck-scoped healing strategies.
- [x] Implement deterministic scorecard metrics for coverage, pacing, density, variety, accessibility, interactions, separation, offline readiness, and source refs.
- [x] Emit internal trace artifacts for plan, validation, healing, scorecard, source refs, model/cost placeholders, and export readiness.
- [x] Add redaction checks so traces do not expose PII, answer keys, raw unsafe prose, or provider stack traces.
- [x] Add tests proving the deterministic scorecard complements, not replaces, Layer 4 judge gating.

## Completion notes

- Added typed validation codes/scopes, healing outcomes, expanded deterministic scorecard dimensions, and internal trace artifact fields to the engine result model.
- Added deterministic engine quality validators for registry membership, pacing, source references, objective coverage, media support, teacher-only separation, density, accessibility, surfaces, and export readiness.
- Added scoped healing report mapping for block, slide, plan, and deck repairs using existing healing vocabulary.
- Added redacted internal trace artifacts for plan, deck data, validation, healing, scorecard, source references, model/cost placeholders, and export readiness.
- Verified with `uv run pytest packages/agents/tests/slide_deck_engine/test_engine.py common/contracts/tests/test_slide_deck.py` → `21 passed`.

## Blocked by

- SD-02 SlideDeckEngine skeleton and typed registries.
- SD-05 interaction modules and media policy.

## References

- `docs/adr/040-native-slide-deck-artifact-and-engine.md`
- `docs/adr/042-slide-deck-surfaces-quality-and-release-gates.md`
- `packages/agents/healing.py`
- `packages/agents/teaching_pack/quality.py`
- `packages/quality/layer4_judge/`
- `packages/agents/observability.py`

## Implementation notes

- Reuse the system vocabulary `retry`, `rewrite`, `reroute`, `replan`, `escalate` where it matches existing healing semantics.
- Keep scorecard deterministic and explainable; do not use an LLM to compute structural metrics.
- Do not log raw provider errors or answer keys in teacher/student-visible outputs.
