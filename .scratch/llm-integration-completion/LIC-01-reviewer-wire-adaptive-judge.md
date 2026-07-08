---
title: "Wire AdaptiveJudge as the real reviewer quality gate"
status: done
labels: [llm-integration, reviewer, quality-gate]
created: 2026-07-08
priority: p0
epic: llm-integration-completion
sequence: 1
---

> **Done (2026-07-08).** Implemented in `packages/agents/teaching_pack/quality_runtime.py`
> (`_evaluate_with_adaptive_judge` helper). While implementing, discovered and fixed a
> real bug that would have made this net-negative: `AdaptiveJudge`'s rubric/prompt let
> the model infer HTML-rendering requirements (doctype, brand string, native inputs)
> from ambient context, even though `render_quality` judges pre-render JSON — every
> artifact was failing on phantom "missing_doctype"-style issues against a live 9router
> run. Fixed in `packages/quality/layer4_judge/judge_prompts.py` (explicit scope note:
> judge JSON structure, not rendered HTML) and `rubric_selector.py` (fixed a real
> bug where `_build_criteria_for_type` silently dropped `RubricCriterion.descriptors`).
> Verified against the live 9router (`:20228`, `4omc`), not just mocked — see test
> updates below. No regressions: full `packages/agents/tests/`, `packages/quality/`,
> and related `tests/e2e/` suites compared byte-for-byte against the pre-change
> baseline (same pre-existing failures, zero new ones).

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (reviewer). Do this **first** in the epic — `LIC-02` (content_creator flip to real LLM) increases content variance and depends on a real quality gate being in place before it ships.

## What to build

`packages/agents/teaching_pack/quality_runtime.py:82` unconditionally builds `LiveReviewerQualityGate()` — a heuristic gate whose 4 lenses (`packages/agents/sub_agents/reviewer/live_quality_gate.py`) check substrings (`"http://"`), keyword overlap, and section count, with scores computed as `threshold + 1.0` / `threshold - 3.0` regardless of actual content quality. The real, tested LLM-as-judge (`reviewer_node` in `packages/agents/sub_agents/reviewer/nodes.py`, using `AdaptiveJudge` with G-Eval scoring and 3-judge `majority_vote()` already wired at `packages/quality/layer4_judge/judge_interface.py:229-230`) has zero production callers.

Change `quality_runtime.py` to run both, layered:
1. `LiveReviewerQualityGate` runs first as a cheap format/PII pre-filter (its "http://" external-asset check and structural checks are still useful and nearly free).
2. If the pre-filter passes, call `reviewer_node` (`AdaptiveJudge`) as the real content/pedagogy/presentation quality gate.
3. If the pre-filter fails, fail fast — do not spend an LLM call on an artifact that's already structurally broken.

## Acceptance criteria

- [x] `quality_runtime.py`'s `render_quality` (or equivalent) calls `reviewer_node` for content/pedagogy/presentation judgment; `LiveReviewerQualityGate` is retained only for its format/PII checks (rename or repurpose its role in code/docs to reflect this).
- [x] `ArtifactQualityReport` produced downstream reflects `AdaptiveJudge`'s real `judge_output` (score, `hard_block_violations`, `rubric_version`) instead of the heuristic's `threshold ± N` numbers. (Surfaced as `quality_scores["layer4_reviewer"]`.)
- [x] Existing tests for `reviewer_node`/`AdaptiveJudge` (already passing, per audit) continue to pass; add an integration test proving `quality_runtime` actually calls `reviewer_node` (not just that `reviewer_node` works in isolation) — this is exactly the "wired, not just written" gap the 2026-07-01 audit's methodology targets. (`test_reviewer_live_wiring.py::test_render_quality_invokes_reviewer_layer4_by_default`, rewritten to assert on `AdaptiveJudge`'s shape.)
- [x] `test_no_dark_runtime_modules.py`'s ledger is updated: `reviewer_node`/`AdaptiveJudge` move from (implicitly) dark to a real caller; add a `REQUIRE_WIRED` entry if the lint's convention calls for it.

### Follow-up discovered while implementing (not pre-existing scope, but real)

- [x] Fixed: `RubricSelector._build_criteria_for_type` dropped `RubricCriterion.descriptors` when rebuilding per-artifact-type criteria — descriptor-based scope notes never reached the prompt.
- [x] Fixed: judge system/user prompt now explicitly states the artifact is pre-render JSON (not HTML) and that `teacher_only` sections are stripped before students see them — eliminates false-positive `missing_doctype`/`missing_brand_string`/`answer_key_leakage` verdicts confirmed against a live 9router run.
- [ ] Not fully solved, flagged for awareness: single-sample LLM judgment can still occasionally be overcautious (e.g. flagging plausible-but-not-certain leakage) — this is the general problem `LIC-09`'s N-sample majority-vote pattern addresses for promptfoo; `AdaptiveJudge` already does 3-judge majority voting internally, which should reduce but not eliminate this. Not blocking — no test depends on the judge being lenient on ambiguous content.
- [ ] Test fixes needed and applied in files unrelated to reviewer (they were incidentally exercising `render_quality`'s default path): `test_content_approval_quality_flags.py`, `test_artifact_workflow_node.py` (3 call sites), `tests/e2e/test_teaching_pack_component_driven_flow.py` (3 call sites) — all now inject an explicit passing `quality_gate` stub since they test rendering/wiring, not reviewer content quality.

## Blocked by

Nothing — `AdaptiveJudge`/`reviewer_node` are already real and tested (see `packages/quality/layer4_judge/judge_interface.py`, `packages/agents/sub_agents/reviewer/nodes.py`).

## Blocks

`LIC-02` (content_creator flip) should not ship to production ahead of this.
