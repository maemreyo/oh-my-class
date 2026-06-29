---
title: Pipeline V2 independent Research Engine
status: active-surface-complete
labels: [pipeline-v2, research, search, 9router]
created: 2026-06-27
order: 5
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-004-run-contract-setup-stage]
adr_refs:
  - docs/adr/006-research-engine.md
  - docs/adr/009-quality-healing-and-safety-gates.md
---

## Problem

Search/fetch is currently a helper inside Researcher and produces large raw prompts. V2 needs a reusable Research Engine that searches before planning when helpful, asks for search confirmation when needed, and produces compact briefs for planning and generation.

## Scope

Implement Research Engine MVP.

Agent-ready tasks:

1. Add public contracts for `PrePlanningSearchBrief`, `ResearchBrief`, `EvidenceCitation`, and `ArtifactResearchGuidance`.
2. Add internal models for `SearchPlan`, `SearchQuery`, `RankedSearchCandidate`, `FetchResult`, `ExtractedEvidence`, and source metadata.
3. Implement research need classifier with config-driven policy.
4. Implement query planner with LLM-assisted configurable modes.
5. Implement search collector using 9Router search, with normalization and dedupe.
6. Implement source ranker with deterministic heuristics and optional LLM micro-briefs.
7. Implement fetch collector using 9Router fetch, parallel fetching, timeouts, and cache.
8. Implement evidence extractor that outputs compact snippets and source ids.
9. Implement source brief and cross-source research brief synthesis.
10. Implement optional search plan confirmation gate.
11. Ensure Content Creator receives only curated briefs/guidance, not raw fetched pages.

## Out Of Scope

- Full artifact generation implementation.
- External vector search or long-term corpus indexing.
- Admin UI for research policies.

## Acceptance Criteria

- Pre-planning search can run before Planner when policy says it should.
- Search can be skipped or confirmed through HITL when policy requires it.
- Search/fetch never includes student PII in queries.
- Research output is compact and cites source ids.
- Raw fetched content is not passed to Content Creator.
- English and Math research plans produce targeted queries, not just topic search.

## Test Plan

- Unit tests for normalization, dedupe, scoring, budget policy, cache keys, and safety scrubbing.
- Integration tests with real 9Router search/fetch for at least one Math and one English scenario.
- Gate tests for search plan confirmation.
- Privacy tests that student identifiers are blocked or scrubbed before search.

## Observability

- Persist events for search plan created, search started/completed, fetch counts, selected sources, and brief created.
- Langfuse metadata includes query count, fetch count, source domains, source ids, and hashes, not raw pages.

## Required Edge Cases And Tests

- Query planner generates more than one purposeful query for Math misconception and English ESL scenarios.
- Search plan confirmation triggers for sensitive, high-budget, ambiguous curriculum, or teacher-source conflict cases.
- Teacher-provided sources are preferred but still fetched/verified and can be flagged as uncertain or contradictory.
- Search results are normalized across duplicate URLs, tracking params, fragments, http/https variants, and same-domain duplicates.
- Blocked domains are excluded; preferred domains rank higher but do not bypass verification.
- Fetch failures, timeouts, non-HTML content, empty pages, redirects, and inaccessible teacher-provided URLs do not fail the whole run.
- Raw fetched pages are not persisted by default and are not passed to Content Creator.
- Source diversity caps prevent all sources coming from one domain.
- Research cache respects TTL and does not leak between tenants.
- Evidence extraction preserves source ids and does not invent claims.
- LLM source summaries are rejected if they introduce claims not supported by excerpts.
- Live 9Router search/fetch tests cover Vietnamese Math, English ESL, and Science citation scenarios.
- Privacy tests prove student names, emails, scores, and class identifiers are stripped from search queries.

## Rollback

Disable pre-planning search in config only if Research Engine blocks V2 cutover; post-blueprint compact research remains required before production release.

## Ultrawork Review — 2026-06-27

Historical status: PARTIAL as of 2026-06-27. The independent research engine MVP was implemented with deterministic tests; the active-surface live 9Router proof was added later in the 2026-06-29 closure below.

Evidence:
- Research contracts are in `common/contracts/research_brief.py`.
- Research planning, URL normalization, ranking, safety, collection, and 9Router provider mapping are implemented in `services/gateway/research_engine.py`, `research_urls.py`, `research_safety.py`, `research_collector.py`, `research_provider_9router.py`, and `research_gate.py`.
- Tests cover targeted Math/English plans, PII scrubbing, dedupe/ranking, compact brief output, fetch failures, search gate behavior, and provider mapping in `services/gateway/tests/test_research_engine.py`, `test_research_collector.py`, `test_research_gate.py`, and `test_research_provider_9router.py`.

Historical gaps and active-surface disposition:
- Closed for the active `/teaching-packs/*` surface: `.scratch/pipeline-v2/artifacts/live-v2-research-transport-2026-06-29.json` records live 9Router `4omc.search` and `4omc.fetch` evidence on `http://localhost:20228/v1` for Vietnamese Math, English ESL, and Science citation scenarios. Each scenario returned search results, citation ids, and compact research briefs with max key finding length ≤ 240 chars.
- Closed for the active `/teaching-packs/*` surface: raw fetched pages remain outside the produced compact briefs; the live artifact records `raw_content_in_brief: false` for all three scenarios.
- Fetch collection is sequential in `services/gateway/research_collector.py`; parallel fetching, timeout policy, and research-cache TTL behavior were not verified.
- Research need classification and query planning are mostly deterministic/hardcoded; config-driven policy and LLM-assisted planning modes were not found.
- Search plan confirmation covers ambiguous curriculum/high-budget cases, but sensitive-source and teacher-source-conflict confirmation paths were not verified.

## Active-Surface Closure — 2026-06-29

Status: COMPLETE for the current Teaching Pack cutover surface.

Evidence:
- Focused deterministic gate: `uv run pytest services/gateway/tests/test_research_engine.py services/gateway/tests/test_research_collector.py services/gateway/tests/test_research_gate.py services/gateway/tests/test_research_provider_9router.py packages/agents/tests/llm/test_transport_policy.py packages/agents/tests/llm/test_json_strategy_policy.py packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_researcher_evidence.py -q` → 50 passed.
- Focused strict typing: `uv run basedpyright services/gateway/research_engine.py services/gateway/research_collector.py services/gateway/research_gate.py services/gateway/research_provider_9router.py packages/agents/llm/transport_policy.py packages/agents/llm/chat_context.py packages/agents/sub_agents/researcher/nodes.py packages/agents/sub_agents/researcher/evidence.py services/gateway/tests/test_research_engine.py services/gateway/tests/test_research_collector.py services/gateway/tests/test_research_gate.py services/gateway/tests/test_research_provider_9router.py packages/agents/tests/llm/test_transport_policy.py packages/agents/tests/llm/test_json_strategy_policy.py packages/agents/tests/sub_agents/test_researcher.py packages/agents/tests/sub_agents/test_researcher_evidence.py` → 0 errors.
- Live 9Router evidence: `.scratch/pipeline-v2/artifacts/live-v2-research-transport-2026-06-29.json` proves Vietnamese Math, English ESL, and Science citation scenarios produce compact cited briefs using `4omc.search` and `4omc.fetch` through `http://localhost:20228/v1`.
