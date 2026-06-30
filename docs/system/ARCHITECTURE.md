# oh-my-class — System Architecture (as-built)

> Written 2026-06-30 from a fresh, evidence-based codebase audit (6 parallel readers, file:line verified).
> This documents **what is actually wired and running**, distinguishing it from modules that exist but are **not invoked**. Status legend: ✅ wired & functional · 🟡 wired but thin/partial · ⚪ exists but **not wired** · 🔴 stub/broken.

---

## 1. What it is

AI teaching-pack generator for K-12 (Vietnam-first). A teacher describes a lesson; the system runs a multi-stage LangGraph pipeline (with teacher approval gates) and produces standalone, print-ready HTML artifacts (lesson, worksheet, quiz, drill, recap, infographic, …).

### Stack (verified)
| Layer | Tech | Notes |
|---|---|---|
| Orchestration | LangGraph 1.x | single 8-stage graph + `interrupt()` gates + Postgres checkpointer |
| Backend | FastAPI (Python 3.12) | gateway on **:8101** (dev; per Makefile + FE default) |
| Frontend | **Next.js 16.2 / React 19.2** | App Router, TanStack Query + Zustand, Tailwind 4 |
| Renderer | Eta (TS) via **Node subprocess** | standalone HTML; DOMPurify/sanitize-html |
| LLM | OpenAI-compatible → **9Router** | all agents use alias **`4omc`** |
| LLM proxy (prod) | LiteLLM :4000 | optional; dev calls 9Router directly |
| Cache | Redis 7 | ephemeral (noeviction, no persistence) |
| DB | PostgreSQL 16 | runs, checkpoints, contracts, jobs, snapshots, events |
| Observability | Langfuse v3 | integrated, degrades gracefully if unconfigured |
| Validation | Pydantic v2 → Zod (codegen) | Python is source of truth |

> **Port note:** code default for the LLM endpoint is `http://localhost:20128/v1`, but `.env` uses `:20228`. Gateway is `:8101` in dev. (Older docs said `:8001` — incorrect.)

---

## 2. Runtime topology — ONE graph

There is a **single authoritative runtime**: the teaching-pack 8-stage graph. The older 18-node `build_oh_my_class_graph` has been **removed**, and the legacy `/run` create + `/run/approve` routes return **HTTP 410** (decommissioned).

```
Teacher (Next.js :3000) ──REST/SSE──▶ FastAPI gateway :8101
                                         │
   POST /teaching-packs/runs  ──▶ create Run + enqueue RunJob (Postgres)
                                         │
   background worker (claim, 120s lease, SKIP LOCKED) ──▶ graph.ainvoke()
                                         │
              teaching-pack StateGraph (LangGraph + Postgres checkpointer)
                                         │
   gate interrupt() ──▶ run pauses ──▶ teacher resumes ──▶ new RESUME job
```

`packages/agents/graph.py` (legacy) — **removed**. `packages/agents/state.py::OhMyClassState` — **legacy, unused** (the runtime uses an inline `TeachingPackState`).

### System diagram — runtime flow

```mermaid
flowchart TB
  Teacher["👩‍🏫 Teacher — Next.js dashboard :3000"]
  subgraph GW["FastAPI gateway :8101"]
    API["routers/teaching_pack_runs<br/>create · resume"]
    JOBS[("run_jobs<br/>SKIP LOCKED · 120s lease · idempotency")]
    WORKER["worker (single, in-process)<br/>+ sweeper 60s"]
    SSE["SSE /status<br/>(teaching_pack_event_bus)"]
  end
  subgraph GRAPH["teaching-pack StateGraph (LangGraph + Postgres checkpointer)"]
    direction TB
    S1["setup_contract"] --> S2["preplanning_search"] --> S3["planning_blueprint<br/>→ planner_node"]
    S3 --> S4["post_blueprint_research<br/>→ researcher_node"] --> S5["artifact_workflow<br/>→ content_creator_node"]
    S5 --> S6{"render_quality<br/>🟡 thin: schema+regex+coherence<br/>+ healing routing"}
    S6 -->|recover| S3
    S6 -->|ok| S7["teacher_approval<br/>interrupt() 🔴 HITL"]
    S7 -->|reject scoped| S5
    S7 -->|approve| S8["export_finalize<br/>ExporterRegistry (HTML ✅)"]
  end
  RENDER["Node subprocess<br/>renderer (Eta) → standalone HTML"]
  LLM["llm_client → 9Router :20228 (host) → 4omc<br/>(prod: + LiteLLM :4000)"]
  DB[("PostgreSQL: runs · contracts · gates · snapshots · events")]

  Teacher -->|POST create/resume| API
  API --> JOBS --> WORKER -->|ainvoke| GRAPH
  S3 & S4 & S5 -.LLM call.-> LLM
  S5 --> RENDER
  S8 --> RENDER
  GRAPH --> DB
  S7 -.interrupt.-> SSE -.live events.-> Teacher
  SSE -.gate pending.-> Teacher --> API
```

### Component layers (status)

```mermaid
flowchart LR
  subgraph FE["Frontend (Next.js 16.2)"]
    UI["runs · runs/new · runs/[id] · approvals<br/>gate-shell · methodology"]
  end
  subgraph BE["Gateway + Pipeline (Python)"]
    direction TB
    PIPE["8-stage graph ✅"]
    SUB["sub-agents: planner·researcher·content_creator<br/>·reviewer ·(diagnostician·roadmap unused)"]
    QUAL["quality: thin gate 🟡 · 6-layer ⚪ not injected<br/>· healing ✅"]
    MW["middleware (30) ⚪ wired to NOTHING"]
    EXP["export: HTML ✅ · gift/h5p/qti 🔴 · google_forms ⚪"]
  end
  subgraph DATA["Contracts / Data"]
    CON["common/contracts (Pydantic, source of truth)"]
    ZOD["→ Zod codegen (FE shares types)"]
  end
  subgraph INFRA["Infra"]
    PG[("Postgres 16")]
    RED[("Redis 7")]
    LF["Langfuse v3 ✅"]
    NR["9Router :20228 (host)"]
  end
  FE -->|REST/SSE| BE
  PIPE --> SUB --> QUAL --> EXP
  CON --> ZOD --> FE
  BE --> PG & RED & LF
  SUB --> NR
```


---

## 3. The 8-stage pipeline

`packages/agents/teaching_pack/graph.py` + `stages.py` + `nodes.py`:

```
setup_contract → preplanning_search → planning_blueprint → post_blueprint_research
  → artifact_workflow → render_quality → teacher_approval → export_finalize → END
```

| Stage | Does | Sub-agent |
|---|---|---|
| setup_contract | extract contract/artifact_types | — |
| preplanning_search | build research brief (thin) | — |
| planning_blueprint | lesson plan | ✅ `planner_node` |
| post_blueprint_research | enrich research | ✅ `researcher_node` |
| artifact_workflow | generate artifacts | ✅ `content_creator_node` |
| render_quality | quality check + healing routing | 🟡 thin (see §6) |
| teacher_approval | **HITL `interrupt()`** | — |
| export_finalize | write exports | 🟡 HTML only (see §8) |

**Conditional routing:** after `render_quality` → recovery routes (`planning_blueprint` / `post_blueprint_research` / `artifact_workflow` / `teacher_approval`); after `teacher_approval` → `export_finalize` (approve) or `artifact_workflow` (scoped reject).

### Sub-agents (6) — `packages/agents/sub_agents/`
`planner`, `researcher`, `content_creator`, `reviewer`, `diagnostician`, `roadmap_agent`. All invoked as **direct node functions** (`await x_node(state)`) — there are no per-agent StateGraph wrappers in the runtime. `diagnostician`/`roadmap_agent` exist but are **not stages** in the 8-stage graph (no diagnostic/roadmap stage wired).

### Lead agent
`packages/agents/lead_agent/` is a separate `create_react_agent` (tool-using) runtime, **not** the teaching-pack pipeline. The 30-middleware chain (`middleware/registry.py`, `ORDERED_MIDDLEWARE_LIST`) is associated with it and is ⚪ **not wired into the teaching-pack graph**.

---

## 4. Gates (HITL)

Gate registry **exists**: `services/gateway/teaching_pack_gate_registry.py`:
- Gates: `clarification_required`, `contract_confirmation`, `search_plan_confirmation`, `blueprint_approval`, `content_approval`.
- Actions: `answer`, `approve`, `reject`, `edit` (validated per-gate by `validate_gate_response`).

Mechanics: `teacher_approval` stage calls LangGraph `interrupt()`; a `GateInterrupt` row is opened (partial-unique index: one ACTIVE gate per (run, gate_name)); teacher resumes via `POST /teaching-packs/runs/{id}/resume`; a `GateResponse` is recorded; a RESUME `RunJob` is enqueued. Contract edits at `contract_confirmation` bump a `ContractRevision`.

---

## 5. Persistence & control plane

**DB (PostgreSQL, 13 Alembic migrations).** Key models:
- `Run` (run_id, teacher_id, status, lesson_plan, theme, retention_days, soft-delete cols), `Artifact`, `CostLog`.
- `RunStatus` enum (10): pending, planning, researching, generating, reviewing, awaiting_approval, exporting, completed, failed, cancelled. *(No `blocked`/`partially_complete` — unit states would be computed, not persisted.)*
- Control: `RunStatusHistory`, `RunContract` + `ContractRevision`, `GateInterrupt`, `GateResponse`, `RunEvent` (sequenced, visibility TEACHER/ADMIN/INTERNAL).
- Jobs: `RunJob` (kind START/RESUME, status, **idempotency_key UQ**, attempts, **eligible_at**, lease_owner/expires).
- Artifacts: `ArtifactWorkflow` (per-artifact state), `ArtifactSnapshot` (content_hash UQ, teacher + student HTML, renderer/template/theme versions).
- Ops: `Notification` + `NotificationDeliveryRecord`, `BudgetLedgerRecord` (per-run tokens/searches/fetches/retries), `ReleaseEvidence`, `ProviderEvidence`.

**Job execution.** `teaching_pack_job_store.py` (claim with `FOR UPDATE SKIP LOCKED`, 120s lease, idempotency, `eligible_at` for queued/backpressure) → **single in-process worker** (`teaching_pack_worker.run_one`, one job at a time) + **sweeper** every 60s (`sweep_stuck_jobs` resets expired leases / fails after 3 attempts; `sweep_escalated_gates`). Resume is a separate job, so gates do **not** pin the worker.
> ⚠️ Lease is fixed 120s with **no heartbeat** → a stage >120s can be reclaimed mid-run (latent double-execution risk).

**SSE.** `teaching_pack_event_bus.py` = in-memory per-run version counter + waiters, notified after DB commit. `GET /teaching-packs/runs/{id}/status` replays `RunEvent` (visibility=TEACHER) from DB then waits. (`packages/agents/events.py` is a second in-memory bus; not the durable source of truth.)

**Retention/privacy (real):** `retention.py` (per-category windows + per-run override), `soft_delete.py`, `purge.py` (`purge_expired_runs` hard-delete + `purge_student_evidence` PII redaction). PII scrubber `packages/quality/layer2_content/pii.py` is production-grade (VN + EN names, contacts, IDs) with audit log.

---

## 6. Quality — IMPORTANT: thin path is what runs

There are effectively **two** quality systems, and the sophisticated one is **mostly not wired into the live pipeline**.

**What actually runs in `render_quality`** (🟡 `quality_runtime.py` + `quality.py::quality_issues`):
- schema validation (`ArtifactContent.model_validate`), placeholder regex, answer-key-leakage regex, `accessibility.language` presence, and **pack coherence** (quiz↔lesson term alignment, objective alignment, vocabulary coverage, Vietnamese difficulty distribution 40/30/20/10).
- On coherence failure → healing routing (§7). Otherwise sets hardcoded `overall: 8.0, passed: True` and builds snapshots.

**The 6-layer system** (`packages/quality/`) ⚪ **exists but is NOT injected**: `build_teaching_pack_graph(...)` is called in `main.py` with **`quality_gate=None`**, so the `QualityGate` Protocol path (fact-check, age, pedagogical, readability, HTML validator, **G-Eval 3-judge**, export validator) never executes in the teaching-pack run.
- Real modules: `layer2_content/pii.py`, `readability_checker.py`, `methodology.py`; `layer3_html/html_validator.py` (DOCTYPE/external-asset/brand/radio/JS hard-blocks); `layer4_judge/` (G-Eval, majority vote, `hard_blocks.py`).
- 🔴 **Stubbed**: `layer2_content/pedagogical.py` (`metrics = {m: True ...}` — all 7 hardcoded True), `fact_check.py` (returns empty), `age_check.py` (returns True).

**Gateway artifact-workflow quality** (✅ separate, wired): `services/gateway/artifact_workflow.py` runs `validate_artifact_content()` (placeholder / answer-key / PII / accessibility scans) during artifact generation, with `try_heal_artifact()`.

> Net: the live path enforces schema + regex + coherence + (at the gateway artifact layer) PII/answer-key — but **not** fact-check, age-appropriateness, pedagogical metrics, or LLM-judge. HARD_BLOCKS are defined (`layer4_judge/hard_blocks.py`) but only enforced where Layer 3/4 run (i.e. not in the live teaching-pack render_quality).

---

## 7. Healing (✅ wired)

`packages/agents/teaching_pack/healing_runtime.py` → `HealingOrchestrator` (`packages/agents/healing/orchestrator.py`) with strategies **retry → rewrite → reroute → replan → escalate** selected by fail-count/type. Invoked from `render_quality` on quality failure; sets `quality_recovery_route` consumed by `quality_routing.py` (routes back to planning/research/artifact_workflow or escalates to teacher_approval).

---

## 8. Rendering & export

**Render boundary (✅):** `services/gateway/renderer_adapter.py` spawns a **Node subprocess** (`node packages/renderer/dist/agent-renderer.js`) per artifact — JSON via stdin → HTML via stdout, **30s timeout**, fail-closed on error/empty/invalid, post-render standalone validation (DOCTYPE, no external URLs). Called from `artifact_snapshot_service.py`, `teaching_pack_completion.py`, `teaching_pack_export_writer.py`.

**Renderer (✅):** `packages/renderer/` — Eta singleton (`autoEscape:true`), **57 templates** (1 base + 11 pages + 45 components), 3 themes (default/forest/ocean via `common/branding/kits/`), per-artifact-type DOMPurify/sanitize-html configs, SVG sanitizer, external-URL guard (INVARIANT-04). Question registry + 8 question types; 4 scoring strategies incl. **`vietnamese-tf-2025`** (QĐ764 0.1/0.25/0.5/1.0).

**Export (`export_finalize` → `ExporterRegistry`, `packages/agents/teaching_pack/exporters.py`):**
- ✅ **HTML** — functional (real files).
- 🔴 **gift / h5p / qti** — registry returns **placeholder paths**; the TS exporters (`packages/exporters/src/{gift,h5p,qti}`) throw "not yet implemented".
- ⚪ **google_forms** — exporter is fully built (OAuth `auth.ts`, `client.ts` createForm/batchUpdate, `question-mapper.ts`) but the registry raises `UnsupportedExportFormatError` (in `_UNSUPPORTED_FORMATS`).
- ✅ **anki-apkg / flashcard-tsv** — implemented in `packages/exporters/src/` (functional, not invoked by the teaching-pack flow).

---

## 9. LLM routing

- **Model config** `packages/agents/config/models.py`: every agent/task uses alias **`4omc`** (no per-tier differentiation, no version pinning); per-agent `max_tokens` caps.
- **Client paths**: `packages/llm_client/` (modern, OpenAI SDK + cost tags + `TokenBudgetManager` soft/hard limits) · `packages/agents/llm/transport.py` (legacy) · `lead_agent` uses LangChain `ChatOpenAI`. Endpoint = `LLM_BASE_URL` (9Router; code default `:20128`, `.env` `:20228`).
- **Cost tags** (INVARIANT-07): `build_tags()` attaches `agent/task/run/step` metadata as `extra_body` (LiteLLM logs it; 9Router ignores).
- ✅ **9Router runs on the host (by design)**: the dev/operator runs 9Router locally on `:20228` and agents call it directly via `LLM_BASE_URL`. `services/router/Dockerfile` is an intentional placeholder because 9Router is **not containerized** — it lives on the host. For the current single-operator (dev = teacher) setup this is the correct topology, not a defect. (If/when multi-tenant hosting is needed, 9Router would be containerized or replaced.)
- ✅ **LiteLLM** proxy is a real image (`ghcr.io/berriai/litellm`), prod-only, routes → 9Router, `max_budget=0` (no paid fallback).
- ✅ **Langfuse** tracing integrated (`observability/tracing.py` `trace_node`/`trace_llm_call`), degrades to no-op when unconfigured.

---

## 10. Frontend (`apps/web/`)

Next.js 16.2 / React 19.2. Routes under `(dashboard)/`: `runs` (list), `runs/new` (create + methodology picker), `runs/[runId]` (detail + live SSE gates), `approvals`. `middleware.ts` gates the dashboard on the `auth-token` cookie. State = TanStack Query (server) + Zustand (UI).

- API client `lib/api-client.ts` → gateway (default `:8101`), Bearer from cookie, X-Request-ID.
- `hooks/use-teaching-packs.ts`: create/resume mutations + **SSE consumer** (`/teaching-packs/runs/{id}/status`, named events, backoff, lastEventId). Legacy `use-run.ts`/`use-approval.ts` still present (some stubbed: `usePendingApprovals` returns []).
- Gate UI: `teaching-packs-gate-shell.tsx` + `teaching-packs-gate-bodies.tsx` (clarification / contract / search-plan / blueprint / content-approval bodies; content-approval shows snapshot preview iframes student/teacher).
- **Methodology system** (`components/methodology/`): 9 tags from the codegen'd `methodology_registry`, compatibility/conflict rules, inverse-thinking editor.
- 🔴 Stubs: login page / JWT verify in `middleware.ts` (presence-only), `usePendingApprovals`.

> No `/units` route, no effectiveness/outcome UI — those features are **planned, not built** (see §13).

---

## 11. Contracts & schema codegen

Pydantic in `common/contracts/` is the **source of truth**: `run_contract`, `lesson_plan` (+ `MethodologyMetadata`), `artifact`, `quality`, `judge_output`, `inverse_thinking`, `methodology_registry` (9 tags), `diagnostic_report`, `research_*`, `roadmap`, `rubric`, `student_profile`, component models.

Codegen (`scripts/generate_zod_schemas.py`): Pydantic → JSON Schema → Zod TS in `common/schemas/src/generated/` for `lesson_plan`, `artifact`, `judge_output`, `inverse_thinking`, `methodology_registry`. Parity enforced by `scripts/verify_schema_parity.py`; FE API types verified by `scripts/verify_frontend_api_contracts.py`. FE transport types (`teaching-pack-api.ts`) are hand-written + verified.
> 🟡 **No `schema_version`** on any contract yet (despite ADR-012 calling for it).

---

## 12. Infrastructure

`infra/compose/docker-compose.yml`: `db` (PG16), `redis` (auth, noeviction), `gateway`, `proxy` (LiteLLM), `web`, `langfuse-web` + `clickhouse` + `minio` (+ `langfuse-worker` profile).
- 🟡 `docker-compose.prod.yml` declares `litellm.depends_on: 9router: service_healthy` but no `9router` service is defined — because **9Router runs on the host, not in compose** (intended for the current single-operator setup). The dangling `depends_on` should be removed (or 9Router containerized) before any multi-host prod deploy; harmless for solo/dev.
- Dev defaults in `.env` (`POSTGRES_PASSWORD=omc_dev`, `REDIS_AUTH=…`, `LANGFUSE_ENCRYPTION_KEY=000…`) must be overridden for prod; **no startup guard** enforces this.
- Packaging: `uv` workspace (Python) + `import-linter` boundaries; `pnpm`/Turborepo + Biome (TS).

---

## 13. Hard invariants (enforced)

INVARIANT-04 no external URLs in HTML (post-render guard) · INVARIANT-05 answer keys teacher-only (regex + sanitizer) · INVARIANT-06 teacher gate via `interrupt()` (24h TTL → escalate) · INVARIANT-07 LLM calls carry metadata tags · INVARIANT-08 clarification middleware last · INVARIANT-10 contracts canonical in `common/contracts`.

---

## 14. Reality check — wired vs. not, and what's planned

**Wired & functional (✅):** single 8-stage graph · sub-agents (planner/researcher/content_creator) · gate registry + HITL interrupt/resume · job queue/worker/sweeper · checkpointer · SSE · healing · HTML render (Node subprocess) · gateway artifact-workflow quality (placeholder/answer-key/PII/accessibility) · retention/purge/PII · Langfuse · methodology system + Zod codegen · frontend create/monitor/approve.

**Wired but thin/partial (🟡):** `render_quality` (schema+regex+coherence only) · export (HTML only) · single in-process worker, fixed lease no heartbeat · no schema_version.

**Exists but NOT wired (⚪):** the 6-layer quality system (`packages/quality`, incl. G-Eval judge) — `quality_gate=None` · 30-middleware chain (lead-agent only) · google_forms/anki/flashcard exporters · diagnostician/roadmap as pipeline stages · legacy `OhMyClassState`.

**Stub / broken (🔴):** `pedagogical.py` / `fact_check.py` / `age_check.py` metrics · gift/h5p/qti exporters · auth login + FE JWT verify · `.env` secret defaults.

**By design for solo-operator (not defects):** 9Router on host (not containerized) · single in-process worker · LiteLLM optional/prod-only.

**Planned, not built (in `.scratch/`, not in code):** topic-decomposition / multi-session units (ADR-017), learning-outcome effectiveness loop / knowledge-tracing (ADR-019), and the runtime-parity items that close the cliffs above (ADR-018: wire 6-layer, wire export formats, etc.). See `.scratch/ROADMAP.md`.

> **Discrepancy to flag:** `.scratch/ROADMAP.md` marks the `runtime-parity` epic "DONE", but this audit shows legacy decommission ✅ landed while the **6-layer quality injection, multi-format export, and pedagogical de-stub did NOT** — the live quality bar is still the thin path. Treat the cliffs in §6/§8 as open.

---

---

## 15. Keeping this document in sync with the code

Docs drift because they are hand-written and unverified (that's why the previous architecture doc was wrong). The fix (tracked in `.scratch/technical-debt/006`):

1. **Generate the volatile facts** — a script emits `docs/system/architecture.manifest.json` from code: stage list, routers, `RunStatus` values, gate names, migration count, exporter-registry formats, codegen models, and **wiring booleans** (`quality_gate_injected`, `middleware_runner_active`, `lead_agent_present`, `legacy_graph_present`). This doc cites those instead of restating them.
2. **CI drift test** — `tests/test_architecture_sync.py` fails the build when a manifest claim diverges from code (e.g. someone injects/removes the quality gate, adds a stage, or changes export formats). Structural/wiring claims are machine-checked; prose stays human-authored.

Until that lands, re-run the 6-explorer audit before trusting any status here.

---

*Method: 6 parallel read-only explorations across orchestration, gateway/persistence, quality, renderer/export, LLM/infra, frontend/contracts; contradictions resolved by direct re-reading. All claims are file:line-checkable in the current tree.*
