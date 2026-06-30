---
title: BaseStore semantic index for grounding retrieval (gated on embeddings)
status: blocked
labels: [blocked]
created: 2026-06-30
---

## What to build

The **semantic (vector) index** on BaseStore — used **only** for grounding retrieval (the one genuine pgvector need; the other 5 memory concerns in `002a` are exact-key).

- `store.search(query=...)` semantic retrieval over grounding material (curriculum norms / verified findings).
- **Embedding MUST route through `llm_client`/LiteLLM** — no direct OpenAI / no external egress. Rationale: K-12 data privacy, single LLM path (`technical-debt/001`), and cost attribution (INVARIANT-07).
- LiteLLM currently registers only `f.light` / `f.pro` (chat) and **no embeddings route** (`infra/litellm/config.yaml`). This issue includes **registering an embeddings model**:
  - (i) a 9Router embeddings combo, if 9Router supports it; **else**
  - (ii) a **local in-cluster** embedding model (e.g. bge / e5) — zero egress.
- **Gated / feature-flagged**: if no compliant embedding provider is available, `002a` ships without vectors and this issue stays parked. Grounding retrieval falls back to exact-key/keyword until then.

## Acceptance criteria

- [ ] Semantic index serves grounding retrieval; a query returns relevant items.
- [ ] All embedding calls go through `llm_client`/LiteLLM (no external egress); calls are cost-tagged.
- [ ] Feature-flagged so `002a` is unaffected when embeddings are unavailable.

## Detailed test suite

(Real embeddings via `llm_client`; real Postgres-backed Store.)

- [ ] `tests/test_basestore_semantic.py`: grounding retrieval via semantic search returns relevant items; embedding path goes through `llm_client` (no direct provider call).
- [ ] Run `uv run pytest tests/test_basestore_semantic.py -v`.

## Blocked by

- .scratch/agent-interaction/002a-store-substrate.md
- Embedding provider decision (9Router embeddings combo vs local bge/e5) — must route via `llm_client`.
