# System Trace: oh-my-class

oh-my-class is an AI-powered teaching pack generator for K-12 education. A teacher describes a lesson topic, grade, and subject; the system produces a complete, print-and-use HTML teaching pack through a multi-stage LangGraph pipeline with 6-layer quality gates, self-healing, and teacher-in-the-loop approval. The output includes lesson, worksheet, quiz, drill, recap, infographic, slide deck, flashcard deck, roadmap, reading passage, and exit ticket, all rendered as standalone HTML with no CDN dependencies.

**Generated:** 2026-07-11 · **Mode:** full trace · **Source commit:** a5628ed

## Tech stack & key dependencies

- **Language(s):** Python 3.12+ (1057 files), TypeScript 5.x (439 files), HTML (93 files)
- **Framework(s):** FastAPI (gateway), LangGraph (agent orchestration), Next.js 16 (frontend), Eta (template engine)
- **Datastore(s):** PostgreSQL 16 (primary), Redis 7 (circuit breaker, session pub/sub), ClickHouse (Langfuse traces), MinIO (Langfuse object storage)
- **Message broker / queue:** None (in-process job queue with DB-backed lease polling)
- **Key third-party libraries:** LangGraph, FastAPI, SQLAlchemy (async), Pydantic v2, OpenAI SDK (via 9Router sidecar), Langfuse v3, Eta, sanitize-html, Zod, TanStack Query v5, Zustand v5
- **Infra / deployment:** Docker Compose (8 services), GitHub Actions CI

## Modules

| Module | Responsibility | Depends on | File |
|--------|---------------|------------|------|
| `agents` | LangGraph multi-agent pipeline (10-stage state machine, 23-layer middleware, self-healing, HITL gates) | `contracts`, `quality`, `llm-client`, `methodologies` | [modules/agents.md](modules/agents.md) |
| `gateway` | FastAPI composition root, REST API, job queue, quality gate wiring, persistence (PostgreSQL) | `agents`, `contracts`, `quality`, `renderer` | [modules/gateway.md](modules/gateway.md) |
| `quality` | 6-layer quality gate system: schema validation, content rules, HTML checks, LLM-as-Judge, HITL, export readiness | `contracts`, `methodologies`, `llm-client` | [modules/quality.md](modules/quality.md) |
| `renderer` | Eta template engine: ArtifactContent JSON to standalone HTML with inlined CSS, 19 plugins, theme system | `schemas` | [modules/renderer.md](modules/renderer.md) |
| `exporters` | Export format generators: GIFT, H5P, QTI, Anki, flashcard TSV, PPTX, Google Forms | `renderer`, `schemas` | [modules/exporters.md](modules/exporters.md) |
| `web` | Next.js 16 teacher dashboard: run creation, approval gates, slide deck editor, live teaching cockpit | `schemas` | [modules/web.md](modules/web.md) |
| `contracts` | Pydantic v2 models: single source of truth for all data schemas (120+ models across 57 files) | *(leaf)* | [modules/contracts.md](modules/contracts.md) |
| `schemas` | TypeScript Zod schemas + 50+ exercise type definitions (generated from Pydantic + hand-written) | *(leaf)* | [modules/schemas.md](modules/schemas.md) |
| `llm-client` | LLM client wrapper: unified async interface via 9Router, circuit breaker, token budget, cost attribution | `contracts` | [modules/llm-client.md](modules/llm-client.md) |
| `notifications` | Pluggable notification dispatcher: SSE, Telegram, email (stubbed) | *(leaf)* | [modules/notifications.md](modules/notifications.md) |
| `methodologies` | Teaching methodology implementations: inverse-thinking projections into lesson/worksheet/quiz/drill | `contracts` | [modules/methodologies.md](modules/methodologies.md) |
| `infra` | Docker Compose manifests, Dockerfiles, database init scripts | *(leaf)* | [modules/infra.md](modules/infra.md) |

## Entry points

- How to run: `make dev` (local) or `make docker` (Docker stack)
- How to build/test: `make check` (tests + build + linters) or per-language: `pytest` (Python), `pnpm test` (TypeScript)
- Composition root: `services/gateway/main.py` wires FastAPI, agents pipeline, worker, and sweeper at startup
- Full inventory of every route, CLI command, worker, and cron: [entry-points.md](entry-points.md)

## Architecture at a glance

See [system-diagram.md](system-diagram.md) (or [system-diagram.html](system-diagram.html) for the interactive version) for the full module graph and key flows. [data-model.md](data-model.md) covers the database schema. [deployment.md](deployment.md) covers the deployment topology.

## Architecture narrative

oh-my-class is a layered monorepo where strict package boundaries enforce a clear dependency direction: data contracts sit at the bottom (zero outbound imports), domain packages (agents, quality, renderer) depend on contracts, the gateway composes everything, and the web frontend is a UI leaf that talks to the gateway over HTTP. The Python world (agents, quality, gateway) and the TypeScript world (renderer, exporters, web, schemas) never import each other directly. They cross the boundary through two seams: a subprocess call (gateway shells out to `node packages/renderer/dist/agent-renderer.js` and the exporters CLI bridge), and a generated schema bridge (`scripts/generate_zod_schemas.py` turns Pydantic models into Zod schemas).

The dominant runtime pattern is a **job-queue adapter**. Teachers hit the gateway's REST API, which creates a database job. A background worker (`TeachingPackWorker`) polls the `run_jobs` table via claim-lease, dispatches to `TeachingPackExecutor`, which invokes the LangGraph `StateGraph`. The graph runs 10 stages (or 12 with the component-strategist feature flag) with 6 conditional routing decisions and 2 HITL interrupt points. Results flow back via SSE events, and the gateway never executes the pipeline synchronously.

Complexity concentrates in three areas. First, the **teaching pack pipeline** in `packages/agents/teaching_pack/` (42+ files): a 10-stage state machine with parallel artifact fan-out, scoped regeneration on rejection, a vocabulary batch orchestrator, and a component-strategist variant that reorders stages structurally. Second, the **quality gate system** across `packages/quality/` and `packages/agents/`: 6 layers from Pydantic schema validation through FACT protocol fact-checking, HTML hard-block enforcement (16 codes, WCAG AA contrast), a 3-judge AdaptiveJudge with majority vote, deterministic compliance gates, and export readiness. Third, the **middleware chain** with 23 ordered layers handling context injection, content safety, guardrails, pedagogical signals, and clarification, each implementing `before_model`/`after_model` hooks.

The former `agents ↔ llm-client` and `agents ↔ quality` reverse imports were removed by moving provider circuit-breaking and gate thresholds into neutral `common/contracts` modules. `tests/test_architecture_truth_gate.py` rejects a reintroduced production import. The `infra` module is a pure configuration leaf (Docker Compose, Dockerfiles, init scripts), which is expected for infrastructure-as-code.

## Codebase health signals

### Most connected modules

By combined inbound + outbound edges (module-to-module):

1. `gateway` (9) ... depends on agents, contracts, quality, renderer; used by web (HTTP), infra (Dockerfile COPY), tests
2. `quality` (5) ... depends on contracts, methodologies, llm-client; used by agents, gateway
3. `agents` (4) ... depends on contracts, quality, llm-client, methodologies; used by gateway
4. `exporters` (4) ... depends on renderer, schemas; used by gateway (subprocess), agents (test-only)
5. `contracts` (3) ... leaf node; used by agents, quality, gateway

### Dependency cycles

No reverse dependency cycles remain:

Provider circuit-breaking and gate thresholds are neutral contracts in `common/contracts`; `tests/test_architecture_truth_gate.py` rejects a reintroduced production import from `quality` or `llm-client` to `agents`.

### Orphan candidates

- **`infra`** ... Pure infrastructure-as-code (Docker Compose YAML, Dockerfiles, bash init script). Zero Python/TypeScript code, zero imports to/from other modules. Expected for a deployment configuration module, but it's structurally disconnected from the dependency graph. Files: 6.

### Trace coverage

- **Full trace (depth: all public surface + verified edges):** `agents`, `gateway`, `quality`, `renderer`, `contracts`
- **Listed (structure confirmed, edges sampled):** `exporters`, `web`, `schemas`, `llm-client`, `notifications`, `methodologies`
- **Unstated:** `schemas` ... traced in full but trace depth not explicitly declared in module doc footer

All 12 modules were traced. No modules were left uncovered.

## How to build & test

```bash
# Local development (uvicorn, no Docker)
make dev                    # Starts gateway on :8101

# Docker stack
make docker                 # docker compose up (gateway :8001, web :3000, postgres, redis, langfuse)

# Run all checks (tests + lint + typecheck)
make check

# Per-language
pytest                       # Python (packages/agents, packages/quality, common/contracts, services/gateway)
pnpm test                    # TypeScript (packages/renderer, packages/exporters, common/schemas)
pnpm build                   # TypeScript build (renderer + exporters + schemas)
make check-architecture      # Runtime manifest + anatomy freshness + source references
```

### CI pipeline

GitHub Actions runs `make check` which covers: pytest, pnpm test, pnpm build, ruff (Python linter), basedpyright (Python typecheck), biome (TypeScript linter), tsc (TypeScript typecheck), and import boundary checks (INVARIANT-02 enforcement).

## Notes

- `_manifest.json` controls incremental updates; delete it to force a full re-trace
- `_modules.json` persists the slug-to-path mapping across runs
- `_graph.json` is the machine-readable graph snapshot for tooling consumption
- This documentation was generated by tracing actual source code, not by summarizing existing README/comments. See individual module files' "Notes / discrepancies" sections for anywhere prior docs and the code disagreed.
