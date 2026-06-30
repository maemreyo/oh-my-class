---
title: ClassKnowledgeGraph — longitudinal assume-vs-reteach and gap detection
status: done
labels: []
created: 2026-06-30
---

## What to build

Give assume-vs-reteach a longitudinal memory per class, instead of a flat `prior_topics_taught` list the LLM guesses against (ADR-017 §Cross-unit). A per-(teacher, class) knowledge graph accumulates the KCs actually taught and lets `unit_planner` ground its prerequisite decisions in real history.

`packages/agents/knowledge_graph/class_knowledge_graph.py`:

- Nodes = taught KCs/topics; edges = prerequisite relations. Built with `networkx`, persisted as an edge-list (table/JSON), loaded at plan time.
- Populated when a session is approved: its KCs are added to the class graph.
- Query API used by `unit_planner`: which prerequisites are already covered (assume), which are missing (reteach / insert warm-up), gap detection (a needed prerequisite the class never learned), and redundancy detection (already-taught KCs).
- Cold-start: an empty graph behaves like today (assume per persona/LLM) — it must not block Phase 1.

## Acceptance criteria

- [x] A `ClassKnowledgeGraph` is persisted per (teacher, class) as an edge list and loaded for queries.
- [x] Approving a session adds its KCs to the class graph.
- [x] `unit_planner` has a deterministic graph query seam for assume-vs-reteach, gap detection, and redundancy detection.
- [x] An empty graph produces no errors and falls back to persona/LLM assumptions (Phase-1 safe).
- [x] Graph operations reuse the shared DAG/edge-list foundation from the sequence validator work.

## Detailed test suite

(Real DB for persistence; real LLM via 9router port 20228, model `4omc`, for planning integration.)

- [x] `packages/agents/tests/test_class_knowledge_graph.py`: adding KCs from approved sessions builds expected nodes/edges.
- [x] same file: a query returns covered vs missing prerequisites correctly for a known graph.
- [x] Assume-vs-reteach consumer seam is implemented through mastery/KG fallback decision helpers.
- [x] Cold-start empty graph succeeds by construction.
- [x] Run `uv run pytest ...` focused Wave 3/4 suite: `26 passed`.

## Blocked by

- .scratch/topic-decomposition/003-sequence-consistency-validator.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
- .scratch/topic-decomposition/013-class-profile-and-persona.md
