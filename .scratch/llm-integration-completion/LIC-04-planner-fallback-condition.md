---
title: "Planner: replace hard-coded use_staged_planner=True with a real coverage condition"
status: ready-for-agent
labels: [llm-integration, planner]
created: 2026-07-08
priority: p2
epic: llm-integration-completion
sequence: 4
---

> Companion implementation task for ADR-048. Independent of `LIC-01`/`LIC-02`/`LIC-03`.

## What to build

`packages/agents/teaching_pack/nodes.py:327` hard-codes `"use_staged_planner": True`, permanently disabling `planner_node`'s real LLM branch and its `expand_lesson_plan_from_seed` branch (`packages/agents/sub_agents/planner/nodes.py:34-48`). Per ADR-048, replace the literal with a real coverage check: `"use_staged_planner": seed_exists_for(raw_request)` (name TBD), so the LLM fallback is reachable when the staged engine has no matching template.

## Acceptance criteria

- [ ] A real function determines whether `staged_engine` can produce a lesson plan for the given `raw_request`/`class_info` (e.g. checks against known unit/seed topics, or a coverage table `staged_engine` already implies).
- [ ] When coverage is missing, `planner_node` runs its real LLM branch (`nodes.py:50-106`) instead of `staged_engine`.
- [ ] `ensure_seed_alignment`/`PlannerDriftError` still apply when a seed is present, regardless of which branch generated the plan.
- [ ] Add a test proving the fallback actually fires for an uncovered request (currently impossible to test meaningfully since the flag is a literal).

## Blocked by

Nothing.
