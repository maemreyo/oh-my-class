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

> **Port note:** code default and `.env.example` both use the host 9Router endpoint `http://localhost:20228/v1`. Gateway is `:8101` in dev. (Older docs said `:8001` — incorrect.)

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

`packages/agents/graph.py` (legacy) — **removed**. `packages/agents/state.py::OhMyClassState` — **removed**; the runtime uses `TeachingPackState` plus boundary-local `MiddlewareState`, `GateState`, and `NodeState` shapes where needed.

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
    S3 --> S4["post_blueprint_research<br/>→ researcher_node"] --> S5["artifact_workflow<br/>→ content_creator_node<br/>or flag-gated Send fan-out"]
    S5 --> S6{"render_quality<br/>✅ 6-layer gate (rollout-flagged)<br/>+ healing routing"}
    S6 -->|recover| S3
    S6 -->|ok| S7["compliance_gate<br/>deterministic hard-block policy"]
    S7 -->|fail closed| S5
    S7 -->|pass| S8["teacher_approval<br/>interrupt() 🔴 HITL"]
    S8 -->|reject scoped| S5
    S8 -->|approve| S9["export_finalize<br/>ExporterRegistry (HTML/GIFT/H5P/QTI ✅)"]
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
  S8 -.interrupt.-> SSE -.live events.-> Teacher
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
    QUAL["quality: ✅ 6-layer gate injected (rollout-flag)<br/>· Layer-2 real metrics · healing ✅"]
    MW["middleware (30) ✅ call-level runner (G1/G2/G3/G5)"]
    EXP["export: HTML/GIFT/H5P/QTI ✅ · google_forms ⚪"]
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
  → artifact_workflow → render_quality → compliance_gate → teacher_approval → export_finalize → END
```

| Stage | Does | Sub-agent |
|---|---|---|
| setup_contract | extract contract/artifact_types | — |
| preplanning_search | build research brief (thin) | — |
| planning_blueprint | lesson plan | ✅ `planner_node` |
| post_blueprint_research | enrich research | ✅ `researcher_node` |
| artifact_workflow | generate artifacts | ✅ `content_creator_node` imperative batch by default; ✅ flag-gated ADR-020 wave-based `Send` fan-out via `generate_one_artifact` |
| render_quality | quality check + healing routing | ✅ 6-layer gate (see §6) |
| compliance_gate | deterministic hard-block enforcement before teacher approval | — |
| teacher_approval | **HITL `interrupt()`**; fast-lane auto-approval requires `compliance_passed is True` | — |
| export_finalize | write exports | ✅ HTML/GIFT/H5P/QTI (see §8) |

**Conditional routing:** after `render_quality` → recovery routes (`planning_blueprint` / `post_blueprint_research` / `artifact_workflow`) or `compliance_gate`; after `compliance_gate` → `teacher_approval` on pass or `artifact_workflow` on fail; after `teacher_approval` → `export_finalize` (approve) or `artifact_workflow` (scoped reject).

### Partially implemented mode: `vocabulary_batch` (ADR-021 / ADR-022)

`vocabulary_batch` is **contracted, not yet runtime-wired**. It is a specialized mode inside the same Teaching Pack runtime, not a separate vocabulary sidecar app. The user-facing surface may be a Vocabulary Batch Generator, but backend control-plane reuse remains mandatory: runs, jobs, gates, SSE, snapshots, quality, renderer/exporter, and BaseStore memory.

The source-of-truth contracts are now present: `PipelineMode` includes `vocabulary_batch`, `methodology_registry` includes `semantic_anchoring` (`Neo Tư Duy / Neo Mindset`), and `common/contracts/vocabulary_batch.py` defines `VocabularyBatchConfig`, structured `InputNormalizationReport` ready/ambiguous cluster shapes, lexical grounding request/evidence/cache-key contracts, `LexicalGroundingBundle`, `SemanticAnchorCluster`, separate `PracticeSet`, projection refs, cluster statuses, and export policy. `common/contracts/vocabulary_cluster_workflow.py` adds per-cluster workflow lifecycle state, ordered evidence ledger entries, review status, export refs, and structured evidence redaction rules. Generated Zod schemas expose the same shapes under `common/schemas/src/generated/vocabulary_batch.ts`, `common/schemas/src/generated/vocabulary_cluster_workflow.ts`, and the generated methodology registry.

The mode treats a vocabulary cluster as a child workflow unit, not as an `ArtifactType`. A cluster such as `travel / journey / trip / voyage / excursion` becomes a `VocabularyClusterWorkflow` with normalized input, lexical grounding, `SemanticAnchorCluster` RCM data, a separate `PracticeSet`, quality verdict, teacher edits, evidence ledger, and export refs. Gateway persistence now has vocabulary-cluster workflow/evidence SQLAlchemy models, store methods, and migration `019_vocabulary_cluster_workflows`; `FEATURE_VOCABULARY_BATCH_V1` guards runtime availability; `packages/agents/teaching_pack/vocabulary_input_normalizer.py` provides the deterministic free-form InputNormalizer capability; `packages/agents/sub_agents/researcher/lexical_grounding.py` provides the reusable Researcher `lexical_grounding` profile with teacher-only source notes, insufficient-evidence `needs_review`, and deterministic cache keys; `packages/agents/sub_agents/content_creator/semantic_anchor_synthesis.py` provides the reusable ContentCreator `semantic_anchor_synthesis` profile that validates `SemanticAnchorCluster`, retries invalid schema with feedback, fails closed, and exposes a compact student-safe projection; `packages/agents/sub_agents/practice_generator/semantic_anchor.py` provides a reusable PracticeGenerator semantic-anchor profile with four-intent `PracticeSet` validation, difficulty-target prompts, independent retry/fail-closed behavior, and a student projection that excludes answers/rationales; `packages/agents/teaching_pack/vocabulary_batch_orchestrator.py` branches flag-enabled `vocabulary_batch` mode from `_artifact_workflow` into per-cluster workflow/progress/event initialization with configurable async concurrency and typed failure actions; `packages/agents/teaching_pack/vocabulary_memory.py` provides vocabulary-specific BaseStore memory for teacher preferences, class/run context, reusable teacher/shared term distinctions, reviewed-only shared lexical promotion, and exact generated/reviewed cluster snapshots; `packages/quality/semantic_anchoring/gate.py` provides a per-cluster SemanticAnchoringQualityGate with passed/needs_review/failed verdicts, hard-block projection/HTML leakage, teacher-review lexical uncertainty, and quality-result evidence payloads; `packages/renderer/src/semantic-anchor-projections.ts` renders separate teacher/student teaching/practice HTML from the same `SemanticAnchorCluster` + `PracticeSet` contracts while keeping teacher scripts, source notes, edge cases, review flags, answers, rationales, and confidence details out of student projections; `packages/exporters/src/vocabulary-batch/index.ts` packages status-aware offline ZIP exports with root `index.html`, `manifest.json`, per-cluster files, diagnostics-only failed clusters, unapproved `needs_review` student-export withholding, and optional student-safe GIFT/H5P practice exports; `services/gateway/release_evidence.py` renders vocabulary-batch rollout receipts; `apps/web/src/components/vocabulary-batch-normalization-preview.tsx` renders ready and ambiguous clusters separately; `apps/web/src/components/vocabulary-batch-review-editor.tsx` provides cluster status review, warning banners, preview panes, validated field-level edits, approve/regenerate/skip actions, teacher preference events, and `needs_review` student-export withholding; and `apps/web/src/components/vocabulary-batch-dashboard.tsx` provides medium-batch progress/status navigation.

Planned stage shape:

```
setup_contract
  → normalize_vocab_batch_input
  → lexical_grounding
  → semantic_anchor_synthesis
  → practice_generation
  → vocabulary_batch_quality
  → teacher_review
  → export_finalize
```

Agent reuse is capability-based: InputNormalizer returns a structured ambiguity report; Researcher is reused through a `lexical_grounding` profile; content synthesis produces `SemanticAnchorCluster`; `PracticeGenerator` is a reusable assessment capability separated from ContentCreator; Reviewer/quality gates enforce lexical, pedagogical, projection, and standalone-HTML checks. See `.scratch/vocabulary-batch/` for the implementation slices.

### Sub-agents (6) — `packages/agents/sub_agents/`
`planner`, `researcher`, `content_creator`, `reviewer`, `diagnostician`, `roadmap_agent`. All invoked as **direct node functions** (`await x_node(state)`) — there are no per-agent StateGraph wrappers in the runtime. `diagnostician`/`roadmap_agent` exist but are **not stages** in the 8-stage graph (no diagnostic/roadmap stage wired).

### Agent-interaction substrate (as-built constraints)
The agents are **imperative calls inside stage nodes**, not graph nodes themselves — so the planned interaction work is shaped by what the runtime does/doesn't use today:
- 🟡 `Command(goto=…)` is **not used by the live runtime**. Routing is still `add_conditional_edges` returning node-name strings (`route_after_render_quality`, `route_after_teacher_approval`). `Send(…)` is the default artifact-generation path and dispatches artifact waves through `generate_one_artifact`; the old batch path is rollback-only behind `OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1`.
- 🟡 `BaseStore`/`PostgresStore` substrate is wired into `build_teaching_pack_graph(store=...)`; it is used for narrow teacher-memory reads/writes, not as a broad semantic memory layer yet.
- 🟡 The live `TeachingPackState` has reducer-backed artifact fan-out channels (`artifact_chunks`, `artifact_workflow_states`) with order-stable fan-in, duplicate prevention, and current-generation filtering. The default `Send` path reads/writes these channels; rollout evidence covers happy path, expected branch failure, checkpoint/resume, scoped regeneration, and release receipts. The old imperative batch merge is narrowed to `_rollback_artifact_workflow()` and is reachable only through the explicit rollback flag.
- ⚪ `stable_merge_files` exists and is tested, but `exported_files` is not reducer-backed because export fan-out is not wired.
- Inter-agent handoff carries the **full** `lesson_plan`/`research_bundle` in state; `summarizers.py` truncation is **prompt-side inside `content_creator`**, not a lossy graph handoff.
> These constraints are tracked in `.scratch/agent-interaction/` and `.scratch/artifact-send-fanout/`: stage = agent graph-identity; typed seam contracts; BaseStore substrate; state-flag/conditional-edge revision protocol; and ADR-020's wave-based `Send` artifact fan-out. Artifact `Send` fan-out is the default path; the old imperative path is rollback-only.

### Lead agent
The `create_react_agent` runtime (`agent.py`/`node.py`) and `lead_agent_node` bridge have been **removed** (confirmed by `architecture.manifest.json::lead_agent_present=false`). Parked helpers (`config.py`, `recovery.py`, `tools.py`) remain in `packages/agents/lead_agent/` — middleware and sub-agent call sites that still use them retain those references; the ReAct orchestrator itself is gone.

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

**Job execution.** `teaching_pack_job_store.py` (claim with `FOR UPDATE SKIP LOCKED`, 120s lease, idempotency, `eligible_at` for queued/backpressure) → worker (`teaching_pack_worker.run_one`) + **sweeper** every 60s (`sweep_stuck_jobs` resets expired leases / fails after 3 attempts; `sweep_escalated_gates`). Resume is a separate job, so gates do **not** pin the worker. Multi-worker concurrency available via `WORKER_CONCURRENCY` env var (default 1 for solo-operator).
> ✅ **Lease heartbeat active** (`_execute_with_heartbeat()` + `_heartbeat()` loop + `renew_lease()`; interval = `lease_seconds / 3` = 40s). A stage running longer than 40s renews its lease before expiry — no latent double-execution risk.

**SSE.** `teaching_pack_event_bus.py` = in-memory per-run version counter + waiters, notified after DB commit. `GET /teaching-packs/runs/{id}/status` replays `RunEvent` (visibility=TEACHER) from DB then waits. (`packages/agents/events.py` is a second in-memory bus; not the durable source of truth.)

**Retention/privacy (real):** `retention.py` (per-category windows + per-run override), `soft_delete.py`, `purge.py` (`purge_expired_runs` hard-delete + `purge_student_evidence` PII redaction). PII scrubber `packages/quality/layer2_content/pii.py` is production-grade (VN + EN names, contacts, IDs) with audit log.

---

## 6. Quality — 6-layer gate now injected

**What runs in `render_quality`** (✅ `quality_runtime.py` → `GatewayTeachingPackQualityGate` → full 6-layer system):
1. **Fast pre-check** (`quality_issues()`): schema validation, placeholder regex, answer-key-leakage, `accessibility.language`, pack coherence (quiz↔lesson alignment, Bloom coverage, VN difficulty distribution 40/30/20/10).
2. **Layer-2 content** (real metrics, not stubs): `pedagogical.py` (objective-alignment, Bloom, CLT load, misconception-coverage via real proxies; unmeasured metrics excluded from pass), `age_check.py` (Flesch-Kincaid + age-band table), `fact_check.py` (claim verification against `research_bundle` sources; no sources → `unmeasured`), `readability_checker.py`, `pii.py`, `methodology.py`.
3. **Layer-3 HTML** (`html_validator.py`): compatibility validator delegated to the shared compliance policy for DOCTYPE, no external assets, brand strings, native radio, unmanaged JS, answer keys, and accessibility hard-blocks.
4. **Layer-4 G-Eval** (`layer4_judge/`): majority-vote 3-judge scoring; `hard_blocks.py` delegates hard-block classification to the shared compliance policy.
5. **Layer-6 export** readiness check.

Gate is **rollout-flagged** (`OMC_ENABLE_SIX_LAYER_QUALITY`, default `true`): injected as `GatewayTeachingPackQualityGate()` in `lifespan`. Pass threshold: `overall ≥ 7.0` AND no critical/hard-block. On failure → healing routing (§7). LLM-judge layers use 9Router `4omc`.

**Gateway artifact-workflow quality** (⚪ separate module, not the production graph path): `services/gateway/artifact_workflow.py` contains a legacy `ArtifactOrchestrator` with dependency waves, `CapacityLimiter`, per-artifact retry, `validate_artifact_content()`, and `try_heal_artifact()`. The teaching-pack graph does not instantiate it; production artifact generation uses ADR-020 `Send` fan-out in `packages/agents/teaching_pack`, with `_rollback_artifact_workflow()` kept only for explicit rollback.

> Net: the live path runs all 6 layers for each artifact: fast schema/coherence pre-check → real Layer-2 pedagogical/age/fact metrics → delegated HTML/compliance checks → G-Eval 3-judge → deterministic `compliance_gate` → export readiness. Manifest boolean `quality_gate_injected` is machine-verified each CI run.

---

## 7. Healing (✅ wired)

`packages/agents/teaching_pack/healing_runtime.py` → `HealingOrchestrator` (`packages/agents/healing/orchestrator.py`) with strategies **retry → rewrite → reroute → replan → escalate** selected by fail-count/type. Invoked from `render_quality` on quality failure; sets `quality_recovery_route` consumed by `quality_routing.py` (routes back to planning/research/artifact_workflow or escalates to teacher_approval).

---

## 8. Rendering & export

**Render boundary (✅):** `services/gateway/renderer_adapter.py` spawns a **Node subprocess** (`node packages/renderer/dist/agent-renderer.js`) per artifact — JSON via stdin → HTML via stdout, **30s timeout**, fail-closed on error/empty/invalid, post-render standalone validation (DOCTYPE, no external URLs). Called from `artifact_snapshot_service.py`, `teaching_pack_completion.py`, `teaching_pack_export_writer.py`.

**Renderer (✅):** `packages/renderer/` — Eta singleton (`autoEscape:true`), **57 templates** (1 base + 11 pages + 45 components), 3 themes (default/forest/ocean via `common/branding/kits/`), per-artifact-type DOMPurify/sanitize-html configs, SVG sanitizer, external-URL guard (INVARIANT-04). Question registry + 8 question types; 4 scoring strategies incl. **`vietnamese-tf-2025`** (QĐ764 0.1/0.25/0.5/1.0).

**Export (`export_finalize` → `ExporterRegistry`, `packages/agents/teaching_pack/exporters.py`):**
- ✅ **HTML** — functional (real files).
- ✅ **gift / h5p / qti** — registry resolves each; `packages/exporters/src/{gift,h5p,qti}` exporters are functional. Fail-closed: a requested format with no registered exporter raises (never silently falls back to HTML).
- ⚪ **google_forms** — exporter is fully built (OAuth `auth.ts`, `client.ts` createForm/batchUpdate, `question-mapper.ts`) but the registry raises `UnsupportedExportFormatError` (in `_UNSUPPORTED_FORMATS`).
- ✅ **anki-apkg / flashcard-tsv** — implemented in `packages/exporters/src/` (functional, not invoked by the teaching-pack flow).

Export also fails closed when required generated artifacts are unavailable. The graph projects teacher-safe per-artifact statuses (`passed`, `regenerating`, `failed`, `skipped_due_dependency`, `escalated`) before content approval and export; failed/skipped/escalated required artifacts produce an `export_blocked` response with a clear teacher-facing `export_block_reason` instead of a partial silent export.

**Planned vocabulary batch export (ADR-021):** `vocabulary_batch` will package per-cluster teacher/student teaching HTML, teacher/student practice HTML, optional GIFT/H5P practice exports, a standalone offline `index.html`, and `manifest.json`. Export is status-aware: `passed` clusters export all student-safe files; `needs_review` clusters export teacher review files only until approval; `failed` clusters export diagnostics only.

---

## 9. LLM routing

- **Model config** `packages/agents/config/models.py`: every agent/task uses alias **`4omc`** (no per-tier differentiation, no version pinning); per-agent `max_tokens` caps.
- **Client path (single)**: `packages/llm_client/` (OpenAI SDK + cost tags + `TokenBudgetManager` soft/hard limits + call-level middleware runner). All sub-agents route through it. `packages/agents/llm/transport.py` is orphaned (no live importers; guarded by `tests/test_no_legacy_transport.py`). Endpoint = `LLM_BASE_URL` (host 9Router default `:20228`; optional production LiteLLM uses `http://litellm:4000`).
- **Cost tags** (INVARIANT-07): `build_tags()` attaches `agent/task/run/step` metadata as `extra_body` (LiteLLM logs it; 9Router ignores).
- ✅ **9Router runs on the host (by design)**: the dev/operator runs 9Router locally on `:20228` and agents call it directly via `LLM_BASE_URL`. `services/router/Dockerfile` is an intentional placeholder because 9Router is **not containerized** — it lives on the host. For the current single-operator (dev = teacher) setup this is the correct topology, not a defect. (If/when multi-tenant hosting is needed, 9Router would be containerized or replaced.)
- ✅ **LiteLLM** proxy is a real image (`ghcr.io/berriai/litellm`), prod-only, routes → 9Router, `max_budget=0` (no paid fallback).
- ✅ **Langfuse** tracing integrated (`observability/tracing.py` `trace_node`/`trace_llm_call`), degrades to no-op when unconfigured.

---

## 10. Frontend (`apps/web/`)

Next.js 16.2 / React 19.2. Routes under `(dashboard)/`: `runs` (list), `runs/new` (create + methodology picker), `runs/[runId]` (detail + live SSE gates), `approvals`. `middleware.ts` gates the dashboard on the `auth-token` cookie. State = TanStack Query (server) + Zustand (UI).

- API client `lib/api-client.ts` → gateway (default `:8101`), Bearer from cookie, X-Request-ID.
- `hooks/use-teaching-packs.ts`: create/resume mutations + **SSE consumer** (`/teaching-packs/runs/{id}/status`, named events, backoff, lastEventId). Legacy `use-run.ts`/`use-approval.ts` still present (some stubbed: `usePendingApprovals` returns []).
- Gate UI: `teaching-packs-gate-shell.tsx` + `teaching-packs-gate-bodies.tsx` (clarification / contract / search-plan / blueprint / content-approval bodies; content-approval shows snapshot preview iframes student/teacher and teacher-safe per-artifact statuses for partial generation).
- Artifact progress UI: `teaching-packs-artifact-progress.tsx` renders teacher-readable artifact statuses, summaries, and next actions; `use-teaching-packs.ts` consumes REST + SSE status payloads including `artifact_statuses` and `teaching_pack.artifact_workflow.status_changed`.
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
- ✅ `docker-compose.prod.yml` has no dangling `9router` depends_on (removed). **9Router runs on the host, not in compose** — intentional for the current single-operator setup. If/when multi-tenant hosting is needed, 9Router would be containerized or replaced.
- Dev defaults in `.env` (`POSTGRES_PASSWORD=omc_dev`, `REDIS_AUTH=…`, `LANGFUSE_ENCRYPTION_KEY=000…`) must be overridden for prod; **no startup guard** enforces this.
- Packaging: `uv` workspace (Python) + `import-linter` boundaries; `pnpm`/Turborepo + Biome (TS).

---

## 13. Hard invariants (enforced)

INVARIANT-04 no external URLs in HTML (shared compliance policy + renderer/export guards) · INVARIANT-05 answer keys teacher-only (shared compliance policy + sanitizer) · INVARIANT-06 teacher gate via `interrupt()` only after `compliance_gate` passes (24h TTL → escalate) · INVARIANT-07 LLM calls carry metadata tags · INVARIANT-08 clarification middleware last · INVARIANT-10 contracts canonical in `common/contracts`.

---

## 14. Reality check — wired vs. not, and what's planned

**Wired & functional (✅):** single 8-stage graph · sub-agents (planner/researcher/content_creator) · gate registry + HITL interrupt/resume · adaptive gate fast-lane (opt-in threshold; teacher-visible auto-approval event) · job queue/worker/sweeper · checkpointer · SSE · healing (5-strategy) · HTML/GIFT/H5P/QTI/Anki APKG/flashcard TSV render + export · **6-layer quality gate** (rollout-flagged, default on; real Layer-2 metrics, G-Eval 3-judge) · teacher-facing quality flags in content approval · BaseStore teacher/class memory · `generate_one_artifact` graph worker plus default artifact `Send` wave router/fan-in (rollback only via `OMC_ROLLBACK_ARTIFACT_SEND_FANOUT_V1`) · teacher-safe partial artifact status · **call-level middleware runner** (G1/G2/G3/G5) · retention/purge/PII · Langfuse · methodology system + Zod codegen · frontend create/monitor/approve.

**Wired but thin/partial (🟡):** worker pool configurable via `WORKER_CONCURRENCY` (default 1) · no schema_version on contracts.

**Exists but NOT wired (⚪):** google_forms exporter · diagnostician/roadmap as pipeline stages.

**Stub / broken (🔴):** auth login + FE JWT verify · `.env` secret defaults.

**By design for solo-operator (not defects):** 9Router on host (not containerized) · single in-process worker · LiteLLM optional/prod-only.

**Planned, not built (in `.scratch/`, not in code):** learning-outcome effectiveness loop / knowledge-tracing (ADR-019), Wave 2+ features (unit_planner, persona, golden-dataset, Forms-capture, cost-cap, etc.), and the remaining **agent-interaction subsystem** (`.scratch/agent-interaction/`: BaseStore semantic index, bounded revision protocol with state-flag/conditional-edge, interaction observability, reviewer `Send` fan-out). Runtime-parity work (ADR-018: 6-layer gate, middleware runner, export formats, event-bus, sub-agent collapse) is **done** as of 2026-07-01. Artifact `Send` issues `001`–`008` are complete; artifact generation now uses Send by default with rollback-only legacy behavior. Unit decomposition is release-ready behind `FEATURE_TOPIC_DECOMPOSITION_V1`; see `.scratch/ROADMAP.md`.

**New planned vocabulary mode:** `vocabulary_batch` (ADR-021 / ADR-022, `.scratch/vocabulary-batch/`) adds Semantic Anchoring / Neo Tư Duy batch generation. It is documented as planned only: no `PipelineMode` value, cluster workflow table, SemanticAnchor contracts, PracticeGenerator, vocabulary quality gate, or batch export package is wired in the as-built runtime yet.

> **Status (2026-07-01):** All `runtime-parity`, `technical-debt`, `priority-upgrades`, and `artifact-send-fanout` epics are confirmed done. Quality gate injected, middleware runner active, export formats wired (HTML/GIFT/H5P/QTI/Anki APKG/flashcard TSV), legacy decommissioned, model tiering available, teacher memory active, adaptive gate fast-lane emits teacher-visible audit events, and artifact `Send` fan-out is the default teacher-facing partial-status generation path — see `architecture.manifest.json` for machine-verified booleans.

---

---

## 15. Keeping this document in sync with the code

Docs drift because they are hand-written and unverified (that's why the previous architecture doc was wrong). The fix (tracked in `.scratch/technical-debt/006`):

1. **Generate the volatile facts** — `scripts/generate_architecture_manifest.py` emits `docs/system/architecture.manifest.json` from code: stage list, routers, `RunStatus` values, gate names, migration count, exporter-registry formats, model assignments, and **wiring booleans** (`quality_gate_injected`, `middleware_runner_active`, `lead_agent_present`, `legacy_graph_present`, artifact Send worker/reducer/default/rollback status). This doc cites the manifest for volatile lists instead of hand-maintaining them.
2. **CI drift test** — `tests/test_architecture_sync.py` fails the build when the manifest diverges from code (e.g. someone injects/removes the quality gate, adds a stage, or changes export formats). Structural/wiring claims are machine-checked; prose stays human-authored.

---

*Method: 6 parallel read-only explorations across orchestration, gateway/persistence, quality, renderer/export, LLM/infra, frontend/contracts; contradictions resolved by direct re-reading. All claims are file:line-checkable in the current tree.*
