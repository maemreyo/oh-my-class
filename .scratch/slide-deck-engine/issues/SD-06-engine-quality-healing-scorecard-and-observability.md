---
title: Add engine quality, typed healing, scorecard, and observability
status: ready-for-agent
labels: [slide-deck-engine, quality, observability, ready-for-agent]
created: 2026-07-06
---

## Parent

ADR-040 and ADR-042.

## What to build

Make `SlideDeckEngine` self-auditing before the existing pack-level judge runs. The engine should produce typed validation failures, scoped healing attempts, deterministic quality scorecards, and redacted trace artifacts so developers and teachers can understand why a deck was produced or repaired.

The deterministic scorecard should cover objective coverage, pacing fit, text density, visual variety, accessibility completeness, interaction appropriateness, teacher-only separation, offline readiness, and source-reference coverage. Healing should repair the narrowest safe scope: block, slide, plan, or whole deck.

## Acceptance criteria

- [ ] Engine validators return typed failure codes for density overflow, invalid layout/block/interaction, missing alt text, unsupported media, pacing mismatch, missing source refs, teacher-only leak risk, and objective coverage gaps.
- [ ] Healing maps each failure class to a scoped repair strategy and records attempts, outcomes, and final status.
- [ ] Deterministic scorecard is produced for every generated deck and is testable without LLM judge calls.
- [ ] Engine trace artifacts include plan, data, validation report, healing report, scorecard, source-ref map, model/cost metadata placeholders, and export readiness manifest.
- [ ] Trace artifacts are internal only and redact or omit student PII, raw untrusted research prose where inappropriate, answer keys from student-surface diagnostics, and provider stack traces.
- [ ] Existing Layer 4 judge remains the qualitative gate; deterministic scorecard does not replace it.

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
