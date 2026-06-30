---
title: Consolidate LLM access onto a single client (llm_client)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Collapse the three LLM access paths into one so cost-tagging, budget, and (next) the call-level middleware runner apply uniformly.

Current paths (verified): `packages/llm_client/` (modern — OpenAI SDK + `build_tags` cost metadata + `TokenBudgetManager`), `packages/agents/llm/transport.py` (legacy), and `lead_agent` via LangChain `ChatOpenAI` (no metadata injection).

- Make **`packages/llm_client/`** the single path; route every sub-agent (planner, researcher, content_creator, reviewer, diagnostician, roadmap, and future unit_planner/sequence_critic/coherence_judge) through it.
- Migrate callers off `agents/llm/transport.py`; remove it once unreferenced.
- The Lead Agent `ChatOpenAI` path is removed with the Lead Agent itself (issue 004).
- `llm_client` becomes the home for the call-level middleware runner (issue 002).

## Acceptance criteria

- [ ] All sub-agent LLM calls go through `llm_client`; no caller uses `agents/llm/transport.py`.
- [ ] Every call carries cost metadata tags (INVARIANT-07) and respects `TokenBudgetManager`.
- [ ] `agents/llm/transport.py` is removed (or reduced to a thin re-export) with no live importers.
- [ ] Behavior is preserved (golden parity on a representative call per agent).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`.)

- [ ] `packages/agents/tests/test_llm_client_consolidation.py`: each sub-agent issues calls via `llm_client`; tags + budget present; output parity vs prior path on a golden input.
- [ ] `tests/test_no_legacy_transport.py`: no live import of `agents/llm/transport.py` outside tests.
- [ ] Run `uv run pytest packages/agents/tests/test_llm_client_consolidation.py -v`.

## Blocked by

None - can start immediately
