---
title: "Diagnostician: keep deterministic metrics, flip misconception classification + summary to LLM"
status: done
labels: [llm-integration, diagnostician]
created: 2026-07-08
priority: p1
epic: llm-integration-completion
sequence: 3
---

> **Done (2026-07-08).** `_classify_misconceptions_llm` (new) makes one LLM call per
> diagnostic report classifying every distinct error-text group + writing the
> summary; `_misconceptions_and_summary` keeps grouping/`systematicity`/`confidence`/
> `question_ids` exactly as before (deterministic). Verified live against 9router:
> for a 4-answer/3-wrong sample, got real per-misconception titles ("Ignoring
> Numerator in Fraction Comparison", "Misapplication of Subtraction with Negative
> Fractions") and a personalized summary in 4.6s — `overall_error_rate: 0.75` matched
> the deterministic count exactly. Failure mode matches `planner`/`content_creator`'s
> established convention (fail loud via `ValueError`, not a silent fallback) —
> the AC's own wording asked for this; an initial fail-closed-to-placeholder draft
> was corrected before landing.

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (diagnostician). Independent of `LIC-01`/`LIC-02` — can ship in parallel.

## What to build

`packages/agents/sub_agents/diagnostician/nodes.py:110-127`'s `_structured_report` computes `knowledge_gaps`, `bloom_gaps`, `overall_error_rate`, and `severity` directly from student response correctness data — these are objective, correctly-computed numbers and **stay deterministic** (an LLM could hallucinate them; there is no upside).

Two sub-functions are weak and become LLM calls instead:
1. `_misconceptions` (`nodes.py:173-189`) → `_taxonomy_title` (`nodes.py:192-198`) only recognizes 2 hardcoded keyword patterns (`"denominator"`, `"sign"`), falling back to a generic `"Contextual procedural slip"` for everything else.
2. The static `summary` field (`nodes.py:125`, `"Structured diagnostic synthesized per knowledge, Bloom, and misconception dimension."`) is identical for every student — not personalized.

Replace both with one LLM call that takes `wrong_answers` (with their `error` field) plus the already-computed `knowledge_gaps`/`bloom_gaps` as grounding context, and returns richer misconception classification + a personalized narrative summary.

## Acceptance criteria

- [x] `_knowledge_gap`, `_bloom_gap`, `_severity`, `overall_error_rate`, `recommended_level` computation is untouched (still deterministic, still 100% accurate against input data).
- [x] Misconception classification is no longer limited to 2 hardcoded categories; it's grounded in the actual wrong-answer `error` text via LLM. `_taxonomy_title`'s keyword matching was removed entirely (not kept as a hint — the LLM call is cheap enough, per-error-group, and the old 2-keyword matcher added nothing worth preserving).
- [x] `summary` is generated per-student from the actual diagnostic report, not a static string.
- [x] `DiagnosticReport` schema validation still passes — LLM output parsed/validated the same way `planner`/`content_creator` do (fail loud via `ValueError` on parse failure or retry exhaustion).
- [x] New LLM call goes through `LLMClient` via `AgentRuntime`, uses `MODELS.diagnostician`.
- [x] All 45 existing diagnostician tests pass unchanged; full `packages/agents/tests/` sweep shows the same 13 pre-existing (unrelated) failures as the pre-LIC-01 baseline, zero new ones.

## Blocked by

Nothing.
