---
title: BaseStore substrate — exact-key, namespaced, TTL (cross-run memory)
status: done
labels: [done]
created: 2026-06-30
---

## What to build

The native LangGraph cross-run memory **substrate** — `BaseStore` (`PostgresStore`) with exact-key access, hierarchical namespaces, and TTL. **Substrate-first**: none of the cross-run memory concerns exist in code yet, so build the store before the features so they are born on it (zero migration).

- Configure `PostgresStore` and **inject at compile** (`store=`), on the **same Postgres** as the checkpointer (additive — checkpointer = thread state, store = cross-run memory; different primitives, one DB).
- Access in nodes via config / `get_store`.
- Namespace `(teacher, class, concern)` → **cross-tenant isolation by construction** (composes with `hardening/002`).
- **TTL** drives staleness (e.g. research-cache recency window).
- Standardize the 6 cross-run memory concerns on Store namespaces (no bespoke per-feature memory tables):
  - research-cache (`agent-upgrades/001`) — `(teacher, "research_cache", topic_key)`, TTL = recency window.
  - seq-templates (`topic-decomposition/014`) — `(teacher, "seq_templates", key)`.
  - ClassKnowledgeGraph (`topic-decomposition/015`) — `(teacher, class, "knowledge_graph")`.
  - KT mastery (`effectiveness-loop/004`, `agent-upgrades/005`) — `(teacher, class, "kt_mastery")`.
  - teacher-preferences (`topic-decomposition/014`) — `(teacher, "preferences")`.
  - component-effectiveness (`agent-upgrades/003`) — `(teacher, "component_effectiveness")`.
- **No semantic/vector index here** — exact-key only (see `002b` for the grounding-retrieval vector need). Relational tables remain for runs/jobs/gates/snapshots.

## Acceptance criteria

- [ ] A `PostgresStore` is configured and injected into the runtime; nodes access it via config.
- [ ] The 6 memory concerns standardize on BaseStore namespaces (no bespoke per-feature memory tables); referenced epics' issues cross-ref updated.
- [ ] TTL drives staleness; cross-teacher isolation holds by namespace.
- [ ] Relational tables remain for runs/jobs/gates/snapshots (not memory).

## Detailed test suite

(Real Postgres-backed BaseStore.)

- [ ] `tests/test_basestore_namespaces.py`: put/get across the 6 namespaces; cross-teacher isolation by namespace.
- [ ] `tests/test_basestore_ttl.py`: a research-cache entry expires per its TTL (staleness).
- [ ] Run `uv run pytest tests/test_basestore_namespaces.py tests/test_basestore_ttl.py -v`.

## Blocked by

None — can start immediately. (Substrate for `002b`, `td-014/015`, `effectiveness-004`, `agent-upgrades/001/003/005`.)
