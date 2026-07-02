---
title: Researcher — real FACT grounding (triangulation, not LLM-rated credibility)
status: done
labels: [done]
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

- [x] Claims are verified by ≥2-source triangulation; credibility is heuristic, not LLM-rated; fallback never fabricates credibility.
- [x] Verification is targeted to lesson-plan claims through `target_claims_from_lesson_plan()`, scoped factual-only + criticality-tiered.
- [x] `contradicted` vs `unverified` are represented distinctly in the grounding status model; critical escalation remains the gate consumer's policy hook.
- [x] Per-source provenance is persisted through fetched excerpts; partial verification stays explicit through `UNCERTAIN`/ungrounded claims.
- [x] `research_policy` controls rigor thresholds/caps/recency through `policy_rigor()`; recency varies by subject.
- [x] A research-memory cache reuses verified sources per `(topic, grade, locale)` with staleness invalidation.
- [x] The verified corpus is consumed by `fact_check` (no double verification).

## Detailed test suite

(Real LLM via 9router `:20228`/`4omc`; real fetch where feasible.)

- [x] `packages/agents/tests/test_researcher_triangulation.py`: 1 source is not VERIFIED; ≥2 independent sources verify.
- [x] `packages/agents/tests/test_researcher_deterministic_verification.py`: credibility derives from source/fetch/agreement, not an LLM number.
- [x] `packages/agents/tests/test_researcher_grounding.py`: pedagogical statements are skipped; critical factual claims and policy rigor are deterministic.
- [x] `packages/agents/tests/test_researcher_grounding.py`: cache reuses fresh verified sources; stale entries are invalidated.
- [x] `packages/agents/tests/test_fact_check_grounding_corpus.py`: Layer-2 `fact_check` consumes verified corpus without LLM re-verification.

## Verification

```
uv run pytest packages/agents/tests/test_researcher_grounding.py \
  packages/agents/tests/test_fact_check_grounding_corpus.py \
  packages/agents/tests/test_researcher_triangulation.py \
  packages/agents/tests/test_researcher_deterministic_verification.py \
  packages/agents/tests/test_researcher_excerpt_persistence.py \
  packages/agents/tests/test_researcher_lexical_grounding.py -q
# 19 passed
```

## Blocked by

- .scratch/technical-debt/002-middleware-wiring-and-runner.md  (StructuredOutput retry)
