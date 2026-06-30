---
title: SequenceConsistencyValidator and networkx DAG foundation
status: done
labels: []
created: 2026-06-30
---

## What to build

Add the deterministic, pedagogy-grounded validator (ADR-017 quality tier 1) that gates a `LessonSequence` before it reaches the unit approval gate, and unify all DAG operations on `networkx` (replacing hand-rolled DFS).

`packages/agents/middleware/sequence_consistency_validator.py`:

- Acyclic prerequisite DAG (over `prerequisite_sessions` and, when present, `prerequisite_edges`).
- Bloom rule: ≥ 2 distinct levels across the sequence **and** at least one apply-or-higher (vận dụng) level, **unless** the topic is pure-recall (a `pure_recall` exemption).
- Cognitive load: ≤ 4 **new** `knowledge_components` per session (CLT). `recalled_kc_ids` are references and are **never** counted toward the limit.
- Duration drift: total session minutes within ±10–15% of `total_duration_minutes` (HARD).
- Session count: **advisory** check against the grounded norm (warn if far outside; not a HARD gate).
- Prerequisite depth ≤ 3 unmastered levels.
- Returns structured, per-rule issues (not just a boolean), each tagged HARD vs advisory, so they can surface on the gate. Wording frames norms as "operational constraint grounded in PPCT/sample plans," not universal law.

Add `networkx` to `packages/agents` dependencies and use it for topo sort, cycle detection, and ancestor/descendant queries here and (later) in the orchestrator and ClassKnowledgeGraph.

This is a pure-function middleware; it must not call the LLM or touch the DB.

## Acceptance criteria

- [x] `networkx` is declared as a dependency in `packages/agents/pyproject.toml`.
- [x] `SequenceConsistencyValidator` exposes a pure `validate(sequence) -> list[ConsistencyIssue]` (empty list = pass), each issue typed with `rule`, `session_id?`, `severity`, `message`.
- [x] All rules above are implemented using `networkx` for graph checks; CLT counts only `knowledge_components` (new), never `recalled_kc_ids`; session-count is advisory severity.
- [x] The validator is registered in the middleware registry consistent with existing middleware (`packages/agents/middleware/registry.py`).
- [x] Severity distinguishes HARD (block) from advisory so the planner self-repair loop and gate can treat them differently.

## Detailed test suite

(Pure deterministic tests — no DB/LLM needed.)

- [x] `packages/agents/tests/middleware/test_sequence_consistency_validator.py`: a cyclic prerequisite set yields a `cycle` issue; an acyclic one passes.
- [x] same file: a session with 5 **new** KCs yields a `clt_overload` issue scoped to that `session_id`; 4 new + 8 recalled passes (recalled never counted).
- [x] same file: a sequence of only remember+understand on a non-recall topic yields a `bloom_rule` issue; adding an apply level passes; a `pure_recall` topic with one level is exempt.
- [x] same file: a session count far outside the grounded norm yields an **advisory** (non-blocking) issue, not a HARD failure.
- [x] same file: total duration 30% off target yields a `duration_drift` issue; within tolerance passes.
- [x] same file: prerequisite depth 4 yields a `prereq_depth` issue; depth ≤3 passes.
- [x] Property test: `uv run pytest packages/agents/tests/middleware -m property -v` — random acyclic sequences with ≤4 KC/session and ≥2 Bloom levels always pass; injected violations always produce the matching rule.
- [x] Run `uv run pytest packages/agents/tests/middleware/test_sequence_consistency_validator.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md

## Verification

```
uv run pytest packages/agents/tests/middleware/test_sequence_consistency_validator.py -q
```

14 passed.
