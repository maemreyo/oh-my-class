# System Trace: oh-my-class

oh-my-class is an AI-powered teaching pack generator for K-12 education. A teacher describes a lesson topic, grade level, and preferences; the system produces a complete, print-and-use HTML teaching pack — lesson, worksheet, quiz, drill, recap, infographic, slide deck, flashcard deck, roadmap — through a multi-stage LangGraph pipeline with 6-layer quality gates and teacher-in-the-loop approval.

**Generated:** 2026-07-10 · **Mode:** full trace · **Source commit:** HEAD

## Tech stack & key dependencies

- **Language(s):** Python (1057 files), TypeScript (439 files), HTML (93 files)
- **Framework(s):** FastAPI (gateway), LangGraph (agent orchestration), Next.js 16 (frontend), Eta (template engine)
- **Datastore(s):** PostgreSQL 16 (primary), Redis 7 (circuit breaker, session pub/sub), ClickHouse (Langfuse traces), MinIO (Langfuse object storage)
- **Message broker / queue:** None (in-process job queue with DB-backed lease polling)
- **Key third-party libraries:** LangGraph, FastAPI, SQLAlchemy, Pydantic v2, OpenAI SDK (via 9Router), Langfuse, Eta, sanitize-html, Zod, TanStack Query, Zustand
- **Infra / deployment:** Docker Compose (8 services), GitHub Actions CI

## Modules

| Module | Responsibility | Depends on | File |
|--------|---------------|-----------|------|
| `agents` | LangGraph multi-agent pipeline (10-stage state machine) | `contracts`, `quality`, `renderer`, `methodologies` | [modules/agents.md](modules/agents.md) |
| `quality` | 6-layer quality gate system (pure validation library) | `contracts` | [modules/quality.md](modules/quality.md) |
| `renderer` | Eta template engine → standalone HTML (18 plugins) | `schemas` | [modules/renderer.md](modules/renderer.md) |
| `exporters` | Export formats: GIFT, H5P, Anki, TSV, Google Forms | `renderer`, `schemas` | [modules/exporters.md](modules/exporters.md) |
| `gateway` | FastAPI composition root + job queue + HITL gates | `agents`, `contracts`, `quality` | [modules/gateway.md](modules/gateway.md) |
| `web` | Next.js 16 teacher dashboard | `schemas`, `renderer` | [modules/web.md](modules/web.md) |
| `contracts` | Pydantic v2 schema source of truth (120+ models) | *(leaf)* | [modules/contracts.md](modules/contracts.md) |
| `schemas` | TypeScript Zod schemas (generated from Pydantic) | `contracts` | [modules/schemas.md](modules/schemas.md) |
| `llm-client` | LLM client with budget tracking + circuit breaking | `agents` (circuit_breaker) | [modules/llm-client.md](modules/llm-client.md) |
| `notifications` | Pluggable notification channels (SSE, Telegram, email stub) | *(leaf)* | [modules/notifications.md](modules/notifications.md) |
| `methodologies` | Teaching methodologies (inverse thinking) | `contracts` | [modules/methodologies.md](modules/methodologies.md) |
| `infra` | Docker Compose orchestration (8 services) | *(leaf)* | [modules/infra.md](modules/infra.md) |

## Entry points

- How to run: `make dev` (local) or `make docker` (Docker stack)
- How to build/test: `make check` (tests + build + linters) or per-language: `pytest` (Python), `pnpm test` (TypeScript)
- Composition root: `services/gateway/main.py` — wires FastAPI, agents pipeline, worker, and sweeper
- Full inventory of every route/CLI command/worker/cron: [entry-points.md](entry-points.md)

## Architecture at a glance

See [system-diagram.md](system-diagram.md) (or [system-diagram.html](system-diagram.html) for the interactive version) for the full interaction diagram and key flows. [data-model.md](data-model.md) covers the data model. [deployment.md](deployment.md) covers deployment topology.

The system is a **layered monorepo** with strict package boundaries: `contracts` is the leaf (no imports from other packages), `agents` and `quality` depend on `contracts`, `gateway` composes everything, and `web` is the UI leaf. The dominant architectural pattern is a **job-queue adapter**: teachers interact with the HTTP API (gateway), which creates DB jobs, a background worker picks them up and runs the LangGraph state machine, and results flow back via SSE events. The gateway never executes the pipeline synchronously.

The real complexity concentrates in three places: (1) the **teaching pack pipeline** in `packages/agents/teaching_pack/` (42 files, 15 stages, conditional routing, parallel fan-out), (2) the **quality gate system** in `packages/quality/` (6 layers, 16 hard-block codes, 3-judge consensus), and (3) the **component strategy subsystem** in `common/contracts/` (14 files, knowledge-base-backed artifact selection). The pipeline is a state machine with 4 conditional routing decisions and 2 HITL interrupt points.

## Codebase health signals

**Most-connected modules** (by combined Depends-on + Used-by count):

1. `contracts` — 6 inbound connections (agents, gateway, quality, methodologies, schemas, tests)
2. `gateway` — 4 connections (agents→gateway, tests→gateway, gateway→contracts, gateway→quality)
3. `agents` — 4 connections (gateway→agents, tests→agents, scripts→agents, quality→agents)
4. `quality` — 3 connections (agents→quality, gateway→quality, tests→quality)
5. `renderer` — 3 connections (web→renderer, exporters→renderer, agents→renderer)

**Possible dead code / orphan modules:** none found.

**Dependency cycles:** none found.

**Trace coverage:** 12 of 12 modules were traced in full. All modules covered.

## How this was generated

This documentation was generated by tracing the actual source code, not by summarizing existing README/comments. See individual module files' "Notes / discrepancies" sections for anywhere the prior docs and the code disagreed. `_manifest.json` in this folder tracks what was traced, so a future run of this skill can update only what changed — delete it if you ever want to force a full re-trace instead. `_graph.json` in this folder is a machine-readable snapshot of the same module/edge/entry-point graph, for tooling that wants to consume it directly instead of parsing this Markdown.
