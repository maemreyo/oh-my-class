# ADR-006: Research Engine

## Status

**Decided** (2026-06-27) — Pipeline V2 introduces an independent Research Engine module with conditional pre-planning search and compact research briefs.

## Context

The current Researcher calls `web_search(topic)`, fetches several URLs sequentially, truncates raw content, and asks an LLM to produce a ResearchBundle. Live runs show this creates large prompts, long latency, and 504 timeouts. Search is core to teaching pack quality, especially for factual grounding, curriculum alignment, misconceptions, examples, and citations.

The Researcher Agent should not own all search/fetch/rank/extract/synthesize logic as one node.

## Decision

Create an independent Research Engine module.

Public stable contracts live in `common/contracts`, including:

- `ResearchBrief`
- `PrePlanningSearchBrief`
- `EvidenceCitation`
- `ArtifactResearchGuidance`
- `ResearchRiskLevel`
- `ResearchPolicy`

Internal pipeline models live in the Research Engine implementation, including:

- `SearchPlan`
- `SearchQuery`
- `RankedSearchCandidate`
- `FetchResult`
- `ExtractedEvidence`
- source scoring metadata
- cache metadata

The engine is hybrid:

- deterministic core for URL normalization, dedupe, source scoring, cache keys, chunking, source diversity, and hard caps;
- configurable LLM adapters for query planning, search-result micro-briefs, source briefs, cross-source synthesis, and artifact-specific guidance.

Search policy:

- conditional search-before-planning, biased toward search;
- optional `search_plan_confirmation` gate for high-budget, sensitive, ambiguous, or direction-changing searches;
- post-blueprint research creates compact shared and artifact-specific briefs;
- Content Creator receives only curated briefs and citations, not raw fetched pages.

Search/fetch processing:

1. classify research need and risk;
2. plan multiple purposeful queries;
3. search in parallel;
4. normalize and dedupe candidates;
5. rank candidates before fetch;
6. fetch selected sources in parallel with timeouts and cache;
7. extract relevant evidence snippets;
8. synthesize source briefs;
9. synthesize compact research brief;
10. create artifact-specific guidance when needed.

Config is layered through code defaults, YAML policy, `.env` overrides, request overrides, and the resolved RunContract snapshot.

## Consequences

- Research is reusable by pre-planning, post-blueprint, and artifact enrichment.
- LLMs are used where they add value but deterministic logic remains testable.
- Search/fetch no longer floods generation prompts with raw pages.
- Teacher can confirm search direction when it matters.
- Evidence and citations become auditable.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep Researcher as one node | Smaller change | Continues timeout and prompt bloat risk |
| Always search everything | Better grounding | Wastes time and may over-search simple runs |
| No pre-planning search | Simpler | Planner may build on weak assumptions |
| Independent Research Engine | Modular and scalable | Requires new contracts and more tests |
