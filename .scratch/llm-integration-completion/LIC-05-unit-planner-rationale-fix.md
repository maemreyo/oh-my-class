---
title: "Fix unit_planner's misleading rationale string (no LLM step actually runs)"
status: ready-for-agent
labels: [correctness, unit-planner]
created: 2026-07-08
priority: p1
epic: llm-integration-completion
sequence: 5
---

> Companion implementation task for ADR-050. Small, standalone, safe to do immediately.

## What to build

`packages/agents/sub_agents/unit_planner/nodes.py:106`'s `_build_sequence` sets `rationale="retrieve grounding → Curricular-CoT adapt → validate; deterministic seam for unit planning."` on every generated `LessonSequence`. No "Curricular-CoT adapt" (chain-of-thought) step exists anywhere in this file — `unit_planner_node` never imports or calls an LLM. This string actively misleads anyone reading a `LessonSequence` (logs, debugging, downstream consumers) into believing an LLM reasoning step ran.

Replace it with an accurate description, e.g. `"deterministic template seam; no LLM reasoning step (see ADR-050, td-006/td-021)"`.

## Acceptance criteria

- [ ] `rationale` text accurately describes the current deterministic implementation.
- [ ] No behavior change beyond the string — this is a correctness/documentation fix, not a scope change (the actual td-006/td-021 LLM upgrade is separate, larger work).
- [ ] Check for other consumers of `rationale` (UI display, logging, tests asserting exact string) and update them if the exact string is asserted anywhere.

## Blocked by

Nothing.
