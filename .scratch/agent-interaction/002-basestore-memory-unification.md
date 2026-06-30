---
title: Unify cross-run memory onto LangGraph BaseStore
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Several epics independently invented cross-run "memory" stores. LangGraph provides a native primitive — **`BaseStore`** (`PostgresStore`) with hierarchical namespaces, `put/get/search`, **optional semantic (vector) index**, and **TTL**. Unify all cross-run memory onto it instead of ad-hoc per-feature tables.

**Subsume onto BaseStore (one substrate, namespaced):**
- research-memory cache (`agent-upgrades/001`) — namespace `(teacher, "research_cache", topic_key)`, **TTL = recency window** (staleness for free).
- decomposition-memory templates (`topic-decomposition/014`) — `(teacher, "seq_templates", key)`.
- ClassKnowledgeGraph (`topic-decomposition/015`) — `(teacher, class, "knowledge_graph")`.
- KT mastery / knowledge-state (`effectiveness-loop/004`, `agent-upgrades/005`) — `(teacher, class, "kt_mastery")`.
- teacher-preferences (`topic-decomposition/014`) — `(teacher, "preferences")`.
- component-effectiveness (`agent-upgrades/003`) — `(teacher, "component_effectiveness")`.

- Inject the store at graph compile (`store=`); access in nodes via config/`get_store`. Use the **semantic index** for grounding retrieval (the pgvector need) and **TTL** for staleness.
- Keep DB tables only where relational integrity/queries are genuinely needed (runs, jobs, gates, snapshots); memory/knowledge → Store.

## Acceptance criteria

- [ ] A `PostgresStore` (BaseStore) is configured and injected into the runtime; nodes access it via config.
- [ ] The 6 memory concerns above use BaseStore namespaces (no bespoke per-feature memory tables).
- [ ] TTL drives staleness (e.g., research-cache recency); semantic index serves grounding retrieval.
- [ ] The referenced epics' issues are updated to persist via BaseStore (cross-refs reconciled).
- [ ] Relational tables remain for runs/jobs/gates/snapshots (not memory).

## Detailed test suite

(Real Postgres-backed BaseStore.)

- [ ] `tests/test_basestore_namespaces.py`: put/get/search across the 6 namespaces; cross-teacher isolation by namespace.
- [ ] `tests/test_basestore_ttl.py`: a research-cache entry expires per its TTL (staleness).
- [ ] `tests/test_basestore_semantic.py`: grounding retrieval via semantic search returns relevant items.
- [ ] Run `uv run pytest tests/test_basestore_*.py -v`.

## Blocked by

None - can start immediately
