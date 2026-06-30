# Expansion Log — oh-my-class Architecture Research

Started: 2026-06-30T11:38:25+07:00

## Phase 0 — Axes

| # | Axis | Worker Type | Task ID | Status |
|---|------|-------------|---------|--------|
| 1 | Agent orchestration | explore | bg_0b60708e | ✅ complete |
| 2 | Gateway API | explore | bg_ddf5f875 | ✅ complete |
| 3 | Frontend | explore | bg_96ffd93e | ✅ complete |
| 4 | Quality gates | explore | bg_616c0cf4 | ✅ complete |
| 5 | Template/renderer | explore | bg_87f78fbd | ✅ complete |
| 6 | LLM routing | explore | bg_393ecce7 | ✅ complete |
| 7 | Infrastructure | explore | bg_441f0412 | ✅ complete |

## Wave 1 — Results Summary

### Axis 1: Agent Orchestration (5m 52s)
- Full file tree: 100+ files in packages/agents/
- Legacy graph: 18 nodes, 9 conditional edges, 4 routers
- Teaching-pack graph: 8 stages, 2 conditional seams
- State schema: 30+ fields across 12 groups, 2 custom reducers
- Middleware: 30 modules (10 context + 7 quality + 11 safety + 1 terminal + base + registry)
- Sub-agents: 6 (planner, researcher, content_creator, reviewer, diagnostician, roadmap_agent)
- Each sub-agent follows identical 5-file pattern (agent.py, nodes.py, state.py, adapters.py, prompts/)
- Healing: 5 strategies (retry/rewrite/reroute/replan/escalate)
- Gates: 2 HITL (blueprint + content) via LangGraph interrupt()
- Events: in-memory SSE bus (emit_run_event)
- Checkpointing: MemorySaver/SqliteSaver/PostgresSaver per env

### Axis 2: Gateway API (6m 45s)
- FastAPI on :8001, 10 routers, 3 middleware layers
- Two LangGraph runtimes side-by-side (legacy + teaching-pack)
- Teaching-pack: job-queue with lease-based claiming, backpressure, idempotency
- Auth: JWT middleware + Bearer/cookie + require_teacher/require_admin
- SSE: EventSourceResponse for both legacy + teaching-pack paths
- 13 Alembic migrations
- Recovery sweeper: 60s loop for stuck jobs + gate escalation
- Worker loop: claim_next → execute → mark_completed/failed
- DB: PostgreSQL with async SQLAlchemy

### Axis 3: Frontend (2m 3s)
- Next.js 15 App Router, 68 source files
- 5 pages: /approvals, /runs, /runs/new, /runs/[runId], root layout
- shadcn/ui primitives (6), Tailwind, Zustand + TanStack Query
- SSE for real-time teaching-pack progress
- Edge middleware for auth gating
- 11 component files + methodology/ plugin system
- No route handlers — pure API consumer
- Testing: Vitest (unit) + Playwright (e2e)

### Axis 4: Quality Gates (3m 37s)
- Two quality systems: in-pipeline (teaching_pack/quality.py) + 6-layer (packages/quality/)
- In-pipeline: schema validation, placeholder detection, answer-key leakage, pack coherence, Vietnamese difficulty distribution
- 6-layer: Layer1 (schema) → Layer2 (content) → Layer3 (HTML) → Layer4 (LLM judge) → Layer5 (HITL) → Layer6 (export)
- Scoring: Layer1×0.15 + Layer2×0.55 + Layer3×0.30, pass ≥7.0
- 3-judge majority vote for LLM-as-Judge
- QualityGate Protocol boundary (ports.py)
- Healing: 4 attempts (rewrite → reroute → replan → escalate)
- AGENTS.md discrepancy: gates.py is a directory, not a file

### Axis 5: Template/Renderer (5m 53s)
- Eta engine: autoEscape, useWith:false, production cache
- 11 page templates + 45 component templates + base.html
- 3-tier CSS token system (primitive → semantic → component)
- 3 themes: default, ocean, forest (JSON → CSS pipeline)
- 5 security layers: Eta escape, DOMPurify, external URL guard, CSP, SVG sanitizer
- 8 question types with registry pattern
- QTI 2.1 exporter with per-type serializers
- Variant generator for question variants
- Scoring strategies including Vietnamese TF 4-item (QĐ 764)
- Preview server with CSP headers
- INVARIANT-04: validateNoExternalUrls() post-render

### Axis 6: LLM Routing (2m 23s)
- Two-layer proxy: LiteLLM :4000 → 9Router :20128
- 5 virtual models, all $0 budget cap
- 4 combo types: f.light, f.pro, content-fusion, deepseek-compressed
- 3 providers: Kiro AI, OpenCode, Vertex AI
- Fallback chains: gpt-5.4→deepseek-v4-flash→deepseek-free→deepseek-compressed
- Redis exact-match cache (prod only)
- Metadata tags: pipeline, agent, step, run, user, model_alias
- Dev mode: bypass LiteLLM, call 9Router directly

### Axis 7: Infrastructure (3m 47s)
- 9 services: db, redis, gateway, proxy, web, langfuse-web, langfuse-worker, clickhouse, minio
- Langfuse v3 full stack (web + worker + ClickHouse + MinIO)
- Redis: noeviction policy, auth required
- PostgreSQL: single instance, 3 logical databases
- 3 Dockerfiles: gateway, proxy, web
- Python: uv workspace with import-linter boundaries
- TypeScript: pnpm + Turborepo + Biome
- Dev defaults: all hardcoded (MUST override for prod)

## Phase 2 — Expansion Assessment

51 EXPAND leads across all 7 workers. Most are follow-up reads for deeper detail on specific files. Given the user's request for a single .md document, the 7 worker results provide sufficient depth for a comprehensive architecture document. Expansion waves not needed for the current deliverable — the findings are already at system-level depth.

## Phase 4 — Synthesis

✅ COMPLETED: `.omo/ulw-research/20260630-113825/ARCHITECTURE.md` written (12 sections, ~1200 lines)

### Coverage achieved:
- System identity + stack (§1)
- Architecture overview + dual-graph diagram (§2)
- Agent orchestration: state schema, legacy 18-node graph, teaching-pack 8-stage graph, 30 middleware, 6 sub-agents, healing, gates, events, checkpointing (§3)
- Gateway API: FastAPI init, 10 routers, schemas, auth, job queue, worker, sweeper, SSE, DB models, migrations (§4)
- Frontend: Next.js 15 pages, components, hooks, API client, SSE, auth (§5)
- Quality gates: in-pipeline checks, 6-layer system, scoring formula, hard blocks, routing, AGENTS.md discrepancies (§6)
- Template/renderer: Eta pipeline, 11 pages + 45 components, 3-tier tokens, themes, 5 security layers, exercise types, export formats (§7)
- LLM routing: 2-layer proxy, 5 models, 4 combos, fallback chains, config, cost attribution (§8)
- Infrastructure: 9 services, Docker, Redis, PostgreSQL, Langfuse v3, env vars, package management (§9)
- End-to-end data flow diagrams (§10)
- Hard invariants table (§11)
- File index (§12)

### AGENTS.md discrepancies discovered:
1. `packages/agents/gates.py` is actually a directory, not a file
2. `common/contracts/gate_config.yaml` is actually at `packages/quality/gate_config.yaml`
3. `packages/exporters/` (GIFT/H5P) does not exist in current tree
