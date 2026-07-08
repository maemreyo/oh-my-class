---
title: "Wire AdaptiveJudge as the real reviewer quality gate"
status: ready-for-agent
labels: [llm-integration, reviewer, quality-gate]
created: 2026-07-08
priority: p0
epic: llm-integration-completion
sequence: 1
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (reviewer). Do this **first** in the epic — `LIC-02` (content_creator flip to real LLM) increases content variance and depends on a real quality gate being in place before it ships.

## What to build

`packages/agents/teaching_pack/quality_runtime.py:82` unconditionally builds `LiveReviewerQualityGate()` — a heuristic gate whose 4 lenses (`packages/agents/sub_agents/reviewer/live_quality_gate.py`) check substrings (`"http://"`), keyword overlap, and section count, with scores computed as `threshold + 1.0` / `threshold - 3.0` regardless of actual content quality. The real, tested LLM-as-judge (`reviewer_node` in `packages/agents/sub_agents/reviewer/nodes.py`, using `AdaptiveJudge` with G-Eval scoring and 3-judge `majority_vote()` already wired at `packages/quality/layer4_judge/judge_interface.py:229-230`) has zero production callers.

Change `quality_runtime.py` to run both, layered:
1. `LiveReviewerQualityGate` runs first as a cheap format/PII pre-filter (its "http://" external-asset check and structural checks are still useful and nearly free).
2. If the pre-filter passes, call `reviewer_node` (`AdaptiveJudge`) as the real content/pedagogy/presentation quality gate.
3. If the pre-filter fails, fail fast — do not spend an LLM call on an artifact that's already structurally broken.

## Acceptance criteria

- [ ] `quality_runtime.py`'s `render_quality` (or equivalent) calls `reviewer_node` for content/pedagogy/presentation judgment; `LiveReviewerQualityGate` is retained only for its format/PII checks (rename or repurpose its role in code/docs to reflect this).
- [ ] `ArtifactQualityReport` produced downstream reflects `AdaptiveJudge`'s real `judge_output` (score, `hard_block_violations`, `rubric_version`) instead of the heuristic's `threshold ± N` numbers.
- [ ] Existing tests for `reviewer_node`/`AdaptiveJudge` (already passing, per audit) continue to pass; add an integration test proving `quality_runtime` actually calls `reviewer_node` (not just that `reviewer_node` works in isolation) — this is exactly the "wired, not just written" gap the 2026-07-01 audit's methodology targets.
- [ ] `test_no_dark_runtime_modules.py`'s ledger is updated: `reviewer_node`/`AdaptiveJudge` move from (implicitly) dark to a real caller; add a `REQUIRE_WIRED` entry if the lint's convention calls for it.

## Blocked by

Nothing — `AdaptiveJudge`/`reviewer_node` are already real and tested (see `packages/quality/layer4_judge/judge_interface.py`, `packages/agents/sub_agents/reviewer/nodes.py`).

## Blocks

`LIC-02` (content_creator flip) should not ship to production ahead of this.
