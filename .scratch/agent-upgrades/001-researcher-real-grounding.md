---
title: Researcher — real FACT grounding (triangulation, not LLM-rated credibility)
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Make the researcher's grounding real. Today the "FACT protocol" is lip-service: the LLM self-rates credibility (fallback hardcodes 0.5/0.3), there is no cross-referencing, no URL validation, and `research_policy` only controls fetch count. Redesign per the grilled spec (divide-and-conquer; no mega-prompt).

- **Triangulation (deterministic)**: a claim is `VERIFIED` only when **≥2 independent fetched sources agree**. The LLM extracts claims + maps to source spans **per claim** (focused sub-prompts, not one mega-call); code counts agreement → status. No LLM-invented credibility number.
- **Heuristic credibility**: from source-type/TLD (.edu/.gov/publisher), recency, fetch-success, agreement-count — computed, not hallucinated.
- **Targeted verification**: extract the factual claims/key-terms **from the approved lesson_plan** (runs post-blueprint) and verify those — not a broad topic search. **Claim scope** = factual only (definitions/dates/formulas/numbers/science), tiered by **criticality** (critical → full triangulation, minor → light, non-factual/pedagogical → skip).
- **Contradiction ≠ unverified**: distinct `contradicted` (sources disagree) vs `unverified` (no source). Critical+contradicted → surface at the gate; otherwise content_creator must caveat/avoid. High-credibility is a tiebreak signal only, never a silent decision.
- **Fail-closed + `grounding_confidence`**: emit per-claim verification + provenance + an overall `grounding_confidence`; a critical claim contradicting sources escalates; partial verification is valid (verify what you can, mark the rest, never fabricate).
- **Policy → rigor (not just count)**: basic/standard/rigorous map to triangulation threshold + claim coverage + recency window + sources/claim cap; **cost/latency bound + graceful degrade**; recency window by subject; cache (below) respects staleness.
- **Research-memory cache**: cache verified sources keyed `(topic, grade, locale)` for reuse across runs (cost + consistency), invalidated by recency window.
- **Shared corpus**: the verified-source set is the grounding corpus for Layer-2 `fact_check` (`technical-debt/003`) — one mechanism, two consumers.

## Acceptance criteria

- [ ] Claims are verified by ≥2-source triangulation (per-claim sub-prompts); credibility is heuristic, not LLM-rated; fallback never fabricates credibility.
- [ ] Verification is targeted to the lesson_plan's factual claims, scoped factual-only + criticality-tiered.
- [ ] `contradicted` vs `unverified` are distinct; critical-contradicted escalates to the gate; others are caveated downstream.
- [ ] Per-claim provenance + an overall `grounding_confidence` are emitted; partial verification is valid and explicit (no fabrication, no silent UNCERTAIN-and-proceed).
- [ ] `research_policy` controls rigor (threshold/coverage/recency/cap) with cost bounds + graceful degrade; recency varies by subject.
- [ ] A research-memory cache reuses verified sources per `(topic, grade, locale)` with staleness invalidation.
- [ ] The verified corpus is consumed by `fact_check` (no double verification).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`; real fetch where feasible.)

- [ ] `packages/agents/tests/test_researcher_triangulation.py`: a claim with 1 supporting source → not VERIFIED; ≥2 agreeing → VERIFIED; disagreeing → `contradicted`.
- [ ] `test_researcher_credibility.py`: credibility derives from source-type/recency/agreement, not an LLM number; a failed fetch never yields a fabricated credibility.
- [ ] `test_researcher_scope.py`: pedagogical/opinion statements are skipped; critical factual claims get full triangulation.
- [ ] `test_researcher_policy_rigor.py`: basic vs rigorous change threshold/coverage/cap; a budget cap triggers graceful partial verification (marked), not failure.
- [ ] `test_researcher_cache.py`: a second run on the same topic reuses cached verified sources; stale entries are invalidated.
- [ ] Run `uv run pytest -m real_llm packages/agents/tests/test_researcher_*.py -v`.

## Blocked by

- .scratch/technical-debt/002-middleware-wiring-and-runner.md  (StructuredOutput retry)
