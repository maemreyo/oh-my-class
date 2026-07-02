---
title: RISE template-effectiveness signal + 3-layer HITL
status: done
labels: [done]
completed: 2026-07-01
created: 2026-06-30
---

## What to build

Close the cross-student loop (RISE continuous-improvement): feed measured mastery-gain back into content quality signals, with teacher-in-the-loop discipline.

- **Template-effectiveness signal**: aggregate mastery-gain per (template/methodology, KC) across students; feed it into the decomposition-memory template ranking (topic-decomposition 014) so approaches that **actually raise mastery** rise and ineffective ones are flagged for revision. RISE-style trend over iterations, not single-pack verdicts.
- **3-layer HITL (Plot-Ark)**: L1 low-risk regeneration hints auto-apply; L2 effectiveness-driven content changes are **suggested for teacher approval**; L3 advisory insights ("mastery on KC-X is low") are read-only. Effectiveness never silently rewrites content (teacher-centric).
- **Honest attribution**: signals are aggregate/advisory across multiple deliveries; the system does not blame a single artifact (research gap #5). Cold-start / sparse data suppresses the signal rather than acting on noise.

## Acceptance criteria

- [x] Mastery-gain is aggregated per template/methodology×KC across students and feeds topic-decomposition 014 template ranking.
- [x] Effective approaches rank up; consistently ineffective ones are flagged for revision (trend-based, multi-iteration).
- [x] HITL: L1 auto / L2 teacher-approval / L3 advisory — effectiveness changes are never auto-applied to content.
- [x] Signals are aggregate/advisory; sparse data suppresses them (no noise-driven action).
- [x] All effectiveness copy stays honest (no unverified claims).

## Detailed test suite

(Real DB; deterministic aggregation; real LLM where regeneration is exercised.)

- [x] `services/gateway/tests/test_template_effectiveness.py`: a template with consistently higher mastery-gain ranks above a low-gain one in decomposition-memory; a low-gain template is flagged.
- [x] `services/gateway/tests/test_template_effectiveness.py`: an effectiveness-driven change surfaces as a teacher suggestion (L2), not an auto-apply; advisory insight is read-only (L3).
- [x] Sparse-data test: below a data threshold, no template re-ranking occurs (signal suppressed).
- [x] Run `uv run pytest services/gateway/tests/test_template_effectiveness.py -q`.

## Verification

- `uv run pytest services/gateway/tests/test_template_effectiveness.py -q` covers pure aggregation/HITL/sparse-data behavior; DB-marked tests remain explicitly skipped unless a local Postgres fixture is supplied.

## Blocked by

- .scratch/effectiveness-loop/004-bkt-knowledge-tracing-engine.md
- .scratch/effectiveness-loop/005-loop-closure-and-moet-export.md
- .scratch/topic-decomposition/014-decomposition-memory.md
