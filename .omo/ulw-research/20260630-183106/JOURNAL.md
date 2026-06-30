# Ultraresearch Journal: LangGraph Capabilities Research
Started: 2026-06-30T18:31:06+07:00

## Plan (exhaustive, atomic)
### Phase 0 — Axes
1. **Core Architecture** — StateGraph, nodes, edges, conditional routing, state schema, reducers
2. **Multi-Agent Orchestration** — Sub-graphs, supervisor pattern, swarm mode, agent handoffs, map-reduce
3. **Persistence & Memory** — Checkpointer backends (Memory/Sqlite/Postgres), thread-based state, time travel, history
4. **Human-in-the-Loop (HITL)** — interrupt(), breakpoints, approval nodes, resume patterns
5. **Streaming & Observability** — Token streaming, SSE, sub-graph streaming, LangSmith tracing, LangFuse
6. **Deployment & Platform** — LangGraph Platform, server deployment, cloud, self-hosted, cron jobs, webhooks
7. **Local Codebase Usage** — How oh-my-class leverages LangGraph (graph construction, state, middleware, gates)
8. **Ecosystem & Integrations** — LangChain interop, tool integration, LLM providers, partner libs
9. **Advanced Patterns** — Sub-graph composition, map-reduce, branching scenarios, error handling, self-healing
10. **Version & Migration** — Latest version (1.x), breaking changes, v0.x → v1.x migration

### Scenarios (contract)
- All 10 axes covered by at least one dedicated worker
- Every EXPAND lead investigated or closed
- Final report: standalone HTML at docs/reports/langgraph-capabilities-report.html
- Every claim cites a source

### Findings
(to be populated)

### Learnings
(to be populated)

## Wave 1 Results (all 9 workers collected)

### Worker 1: Core API (bg_df9e535e) — ✅ Complete
- Exhaustive StateGraph reference: state schema, nodes, edges, reducers, subgraphs, Send, error handling
- 12 EXPAND leads identified (Pregel internals, managed channels, interrupt protocol, etc.)

### Worker 2: Multi-Agent (bg_387f1c5d) — ✅ Complete  
- Supervisor, swarm, sub-graph, map-reduce, tool-calling, handoffs patterns
- 4 handoff mechanisms, 6 topology types, production pitfalls documented
- 10 EXPAND leads (langgraph-supervisor internals, create_react_agent API, etc.)

### Worker 3: Persistence/HITL (bg_6838d282) — ✅ Complete
- Checkpoint protocol (v4 schema), all checkpointer backends
- Thread-based state, time travel, 3 HITL mechanisms
- Memory tiers (short/long/semantic), BaseStore interface
- 8 EXPAND leads (SDK, Agent Inbox, Redis, Platform docs, etc.)

### Worker 4: Streaming/Deployment (bg_2e8c5b04) — ✅ Complete
- 7 stream modes documented with evidence
- LangGraph Platform 3-tier architecture
- REST API endpoints, auth, stateless vs stateful
- 6 EXPAND leads (webhook payloads, Studio ui_config, etc.)

### Worker 5: Ecosystem (bg_a725ce74) — ✅ Complete
- LangChain integration, 50+ LLM providers, tool system
- TypeScript parity matrix, v1.2 features
- Comparison with CrewAI/AutoGen, v1.0→v1.2 migration
- 15 EXPAND leads

### Worker 6: Codebase (bg_24f6e8d2) — ✅ Complete
- oh-my-class uses 8-stage teaching-pack graph (authoritative)
- Legacy 18-node graph removed from disk (frozen per ADR-017)
- Sub-agents as async functions (not nested graphs)
- 12 gap reads identified

### Worker 7: Teaching-Pack (bg_68749d10) — ✅ Complete
- Full topology: 8 nodes, 2 conditional seams, state mutations
- Port contracts (9 protocols), quality gate wiring
- Scoped regeneration pattern, invariant enforcement
- 15-file directory inventory with line counts

### Worker 8: GitHub Source (bg_24d12f13) — ✅ Complete
- Monorepo layout: 9 packages in libs/
- Pregel BSP engine architecture, channel primitives
- Checkpointer conformance testing suite
- Release history (549 releases), 592 open issues

### Worker 9: Official Docs (bg_0b7e028e) — ⚠️ Partial
- Sitemap 404, limited page discovery
- Documentation structure mapped from known organization
- Resolution plan provided

## Synthesis Written
- SYNTHESIS.md: 10 themes, 15 sources, complete capability matrix

## Now: HTML Report Generation
- Agent bg_5f1d2127 delegated to generate standalone HTML
- Target: docs/reports/langgraph-capabilities-report.html
