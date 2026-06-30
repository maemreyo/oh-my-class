# Ultraresearch Synthesis: LangGraph Capabilities
Workers: 9 · Waves: 1 · Sources: 15+ · Verifications: 0 (documentation research)

## Executive Summary

LangGraph is a **low-level orchestration framework and runtime** for building stateful, long-running agents as directed graphs. Built by LangChain Inc., it uses a **Bulk Synchronous Parallel (BSP)** execution model inspired by Google Pregel. As of v1.2.6 (June 2026), it is the production-default choice for complex AI agent workflows requiring human-in-the-loop, durable execution, and multi-agent coordination.

### Core Capabilities (10 axes covered)

1. **StateGraph** — Declare agents as nodes in a directed graph with typed state, conditional routing, and reducer-based state merging
2. **Multi-Agent** — Supervisor, swarm, sub-graph, map-reduce, and hierarchical topologies
3. **Persistence** — Checkpointing backends (Memory/SQLite/Postgres/Redis), thread-based state, time travel
4. **HITL** — `interrupt()` for human approval gates, resume with `Command(resume=...)`
5. **Streaming** — Token-level, state-level, custom events, sub-graph streaming via SSE
6. **Deployment** — LangGraph Platform (Server/Cloud/Studio), self-hosted Docker, REST API
7. **Observability** — LangSmith, LangFuse, OpenTelemetry native emission
8. **Ecosystem** — LangChain integration, 50+ LLM providers, TypeScript parity
9. **Advanced Patterns** — `Send` map-reduce, `Command` routing, sub-graph composition, retry/timeout policies
10. **v1.x Modern** — Stable API, typed streaming v2/v3, DeltaChannel, node-level caching

## Findings by Theme

### 1. Core Architecture
- StateGraph is the primary entry point; nodes are Python callables, edges are static or conditional
- State schema via TypedDict/Pydantic with `Annotated[T, reducer]` for merge semantics
- `add_messages` reducer for chat history, `operator.add` for list concatenation
- `Command(goto=..., update=...)` unifies routing + state mutation
- `Send(node, arg)` enables dynamic fan-out / map-reduce
- Compilation validates graph topology, computes parallel branches, wires checkpointing

### 2. Multi-Agent Orchestration
- **Supervisor**: Central coordinator routing to specialist sub-agents via tool calls
- **Swarm** (`langgraph-swarm`): Dynamic peer-to-peer handoffs via `create_handoff_tool`
- **Sub-graphs**: Compiled graphs as nodes with state isolation via input/output mapping
- **Map-reduce**: `Send` + `operator.add` reducer for parallel independent tasks
- **Hierarchical**: Nested supervisors for large agent teams
- Each agent can use different models, tools, prompts, and state schemas

### 3. Persistence & Memory
- Three checkpointers: InMemorySaver (dev), SqliteSaver (local), PostgresSaver (prod)
- Thread-based isolation via `thread_id` in config
- Time travel: `get_state_history()`, replay, fork from any checkpoint
- `update_state()` for surgical state mutation
- Long-term memory via `BaseStore` (InMemory/Postgres/Redis) with namespace hierarchy
- Semantic search built into stores via embeddings
- No built-in cron — scheduling is the deployer's concern

### 4. Human-in-the-Loop
- `interrupt(payload)` — suspends node, persists checkpoint, returns resume value
- `Command(resume=...)` — resumes execution with teacher input
- `interrupt_before` / `interrupt_after` — static breakpoints on specific nodes
- Multiple parallel interrupts with resume map (xxh3_128 hexdigest keys)
- Agent Inbox protocol for structured HITL UIs
- SDK streaming resume via `client.runs.stream()` with `join_stream`

### 5. Streaming & Observability
- 7 stream modes: values, updates, messages, custom, checkpoints, tasks, debug
- Token-level LLM streaming via `stream_mode="messages"`
- Sub-graph streaming via `subgraphs=True`
- SSE transport via `POST /threads/{id}/runs/stream`
- LangSmith auto-instrumentation, LangFuse callback, OpenTelemetry native spans
- Per-call metadata tags for cost attribution

### 6. Deployment & Platform
- `langgraph.json` manifest for all deployment tiers
- `langgraph dev` — local dev server with Studio
- `langgraph up` — Docker compose stack
- `langgraph deploy` — push to LangGraph Cloud
- REST API: Assistants, Threads, Runs, Store, Crons, Webhooks
- Authentication: path-based or custom auth handlers
- Stateful (threaded) vs Stateless (threadless) execution modes

### 7. Ecosystem & Integrations
- 50+ LLM providers via LangChain integrations
- LiteLLM proxy support for unified routing
- `@tool` decorator, `ToolNode`, `tools_condition` for tool calling
- `ToolRuntime` injection (state, store, stream_writer)
- TypeScript/JS SDK with near feature parity
- Partner libs: langgraph-checkpoint, langgraph-sdk, langgraph-cli

### 8. Advanced Patterns
- `RetryPolicy` with exponential backoff per node
- `TimeoutPolicy` for hard/idle timeouts (v1.2)
- `error_handler` per-node for saga/compensation
- `RunControl.request_drain()` for graceful shutdown
- `NodeCachePolicy` for TTL'd node output caching
- `DeltaChannel` for incremental checkpointing of large state

### 9. Version & Migration
- v1.0.0 (Oct 2025) — stable API, Python 3.10+ required
- v1.1.0 — typed v2 streaming, GraphOutput
- v1.2.6 (current, Jun 2026) — v3 streaming, DeltaChannel, timeouts, error handlers
- LTS: v1.0+ active until v2.0; v0.4 maintenance until Dec 2026
- Breaking: `create_react_agent` → `create_agent`, `MessageGraph` → `StateGraph`

### 10. Local Codebase Usage (oh-my-class)
- 8-stage teaching-pack graph with 2 conditional seams
- `TeachingPackState` TypedDict with stage tracking, quality scores, gate payloads
- Sub-agents called as async functions (not nested graphs)
- `interrupt()` for teacher approval gate with scoped regeneration
- PostgresSaver for production, MemorySaver for dev
- Custom middleware chain (24 layers) separate from LangGraph runtime
- No LangGraph Platform deployment — embedded in FastAPI gateway

## Sources
1. LangGraph GitHub: github.com/langchain-ai/langgraph (35.8K★, 549 releases)
2. LangGraph OSS Docs: docs.langchain.com/oss/python/langgraph/
3. LangGraph Reference: reference.langchain.com/python/langgraph/
4. Context7: /websites/langchain_oss_python_langgraph (1448 snippets)
5. Context7: /langchain-ai/langgraph (563 snippets)
6. Context7: /langchain-ai/langgraph-swarm-py (441 snippets)
7. Context7: /websites/reference_langchain_python_langgraph (4840 snippets)
8. oh-my-class codebase: packages/agents/teaching_pack/ (15 files)
9. oh-my-class AGENTS.md (architectural reference)
10. LangChain 1.0 GA announcement
11. v1.2.0 changelog
12. v1.2.3 release notes
13. LangGraph 1.0 migration production guide
14. Mega One AI comparison (LangGraph vs AutoGen vs CrewAI 2026)
15. Towards AI comparison article
