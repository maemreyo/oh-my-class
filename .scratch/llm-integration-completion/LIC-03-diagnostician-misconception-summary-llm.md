---
title: "Diagnostician: keep deterministic metrics, flip misconception classification + summary to LLM"
status: ready-for-agent
labels: [llm-integration, diagnostician]
created: 2026-07-08
priority: p1
epic: llm-integration-completion
sequence: 3
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 0b (diagnostician). Independent of `LIC-01`/`LIC-02` — can ship in parallel.

## What to build

`packages/agents/sub_agents/diagnostician/nodes.py:110-127`'s `_structured_report` computes `knowledge_gaps`, `bloom_gaps`, `overall_error_rate`, and `severity` directly from student response correctness data — these are objective, correctly-computed numbers and **stay deterministic** (an LLM could hallucinate them; there is no upside).

Two sub-functions are weak and become LLM calls instead:
1. `_misconceptions` (`nodes.py:173-189`) → `_taxonomy_title` (`nodes.py:192-198`) only recognizes 2 hardcoded keyword patterns (`"denominator"`, `"sign"`), falling back to a generic `"Contextual procedural slip"` for everything else.
2. The static `summary` field (`nodes.py:125`, `"Structured diagnostic synthesized per knowledge, Bloom, and misconception dimension."`) is identical for every student — not personalized.

Replace both with one LLM call that takes `wrong_answers` (with their `error` field) plus the already-computed `knowledge_gaps`/`bloom_gaps` as grounding context, and returns richer misconception classification + a personalized narrative summary.

## Acceptance criteria

- [ ] `_knowledge_gap`, `_bloom_gap`, `_severity`, `overall_error_rate`, `recommended_level` computation is untouched (still deterministic, still 100% accurate against input data).
- [ ] Misconception classification is no longer limited to 2 hardcoded categories; it's grounded in the actual wrong-answer `error` text via LLM, with `_taxonomy_title`'s keyword matching removed or kept only as a cheap pre-classification hint fed into the LLM prompt.
- [ ] `summary` is generated per-student from the actual diagnostic report, not a static string.
- [ ] `DiagnosticReport` schema validation still passes — LLM output is parsed/validated the same way `planner`/`content_creator` validate their LLM output (fail loud on schema mismatch, don't silently accept malformed misconceptions).
- [ ] New LLM call goes through `LLMClient` via `AgentRuntime`, uses `MODELS.diagnostician`.

## Blocked by

Nothing.
