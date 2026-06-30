---
title: ClassKnowledgeGraph — longitudinal assume-vs-reteach and gap detection
status: ready-for-agent
labels: [ready-for-agent]
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

- [ ] A `ClassKnowledgeGraph` is persisted per (teacher, class) as an edge list and loaded into `networkx` for queries.
- [ ] Approving a session adds its KCs to the class graph.
- [ ] `unit_planner` queries the graph for assume-vs-reteach, gap detection, and redundancy detection, and reflects the result in the sequence (e.g. inserts a warm-up when a prerequisite is missing).
- [ ] An empty graph produces no errors and falls back to persona/LLM assumptions (Phase-1 safe).
- [ ] Graph operations reuse the shared `networkx` foundation (issue 003).

## Detailed test suite

(Real DB for persistence; real LLM via 9router port 20228, model `4omc`, for planning integration.)

- [ ] `packages/agents/tests/test_class_knowledge_graph.py`: adding KCs from approved sessions builds the expected nodes/edges; the graph remains acyclic.
- [ ] same file: a query returns covered vs missing prerequisites correctly for a known graph.
- [ ] `packages/agents/tests/test_kg_assume_vs_reteach.py`: with a prerequisite present in the class graph, `unit_planner` assumes it (no reteach session); with it absent, the planner inserts a warm-up / flags a gap.
- [ ] Cold-start test: planning with an empty graph succeeds and matches non-KG behavior.
- [ ] Run `uv run pytest packages/agents/tests/test_class_knowledge_graph.py packages/agents/tests/test_kg_assume_vs_reteach.py -v`.

## Blocked by

- .scratch/topic-decomposition/003-sequence-consistency-validator.md
- .scratch/topic-decomposition/006-unit-planner-agent.md
- .scratch/topic-decomposition/013-class-profile-and-persona.md
