---
title: SequenceConsistencyValidator and networkx DAG foundation
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Add the deterministic, pedagogy-grounded validator (ADR-017 quality tier 1) that gates a `LessonSequence` before it reaches the unit approval gate, and unify all DAG operations on `networkx` (replacing hand-rolled DFS).

`packages/agents/middleware/sequence_consistency_validator.py`:

- Acyclic prerequisite DAG (over `prerequisite_sessions` and, when present, `prerequisite_edges`).
- Bloom coverage ≥ 2 distinct levels across the sequence.
- Cognitive load: ≤ 4 new `knowledge_components` per session (CLT).
- Duration drift: total session minutes within ±10–15% of `total_duration_minutes`.
- Prerequisite depth ≤ 3 unmastered levels.
- Returns structured, per-rule issues (not just a boolean) so they can surface on the gate.

Add `networkx` to `packages/agents` dependencies and use it for topo sort, cycle detection, and ancestor/descendant queries here and (later) in the orchestrator and ClassKnowledgeGraph.

This is a pure-function middleware; it must not call the LLM or touch the DB.

## Acceptance criteria

- [ ] `networkx` is declared as a dependency in `packages/agents/pyproject.toml`.
- [ ] `SequenceConsistencyValidator` exposes a pure `validate(sequence) -> list[ConsistencyIssue]` (empty list = pass), each issue typed with `rule`, `session_id?`, `severity`, `message`.
- [ ] All six rules above are implemented using `networkx` for graph checks.
- [ ] The validator is registered in the middleware registry consistent with existing middleware (`packages/agents/middleware/registry.py`).
- [ ] Severity distinguishes HARD (block) from advisory so the planner self-repair loop and gate can treat them differently.

## Detailed test suite

(Pure deterministic tests — no DB/LLM needed.)

- [ ] `packages/agents/tests/middleware/test_sequence_consistency_validator.py`: a cyclic prerequisite set yields a `cycle` issue; an acyclic one passes.
- [ ] same file: a session with 5 KCs yields a `clt_overload` issue scoped to that `session_id`; 4 passes.
- [ ] same file: a single-Bloom-level sequence yields a `bloom_coverage` issue; ≥2 levels passes.
- [ ] same file: total duration 30% off target yields a `duration_drift` issue; within tolerance passes.
- [ ] same file: prerequisite depth 4 yields a `prereq_depth` issue; depth ≤3 passes.
- [ ] Property test: `uv run pytest packages/agents/tests/middleware -m property -v` — random acyclic sequences with ≤4 KC/session and ≥2 Bloom levels always pass; injected violations always produce the matching rule.
- [ ] Run `uv run pytest packages/agents/tests/middleware/test_sequence_consistency_validator.py -v`.

## Blocked by

- .scratch/topic-decomposition/001-contracts-and-codegen.md
