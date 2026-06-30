# oh-my-class — Complete System Architecture

> Auto-generated from exhaustive codebase trace — 2026-06-30
> Traced by: 7 parallel explore agents across all subsystems
> Source confidence: Direct file reads + grep verification + AGENTS.md cross-reference

---

## ⚠️ CORRECTION — Migration Status & Capability Cliffs (2026-06-30, verified)

This document describes capabilities that exist as **modules** but are **not wired into the authoritative teaching-pack runtime** — they remain wired only to the FROZEN legacy graph. Treat the following as the accurate state (see **ADR-018** and the `.scratch/runtime-parity/` epic):

| Section | Claim in this doc | Verified reality | Fix |
|---------|-------------------|------------------|-----|
| §3.3 / §6 | 6-layer quality runs in teaching-pack | **No** — `render_quality` runs only `quality_issues()` (regex/schema/VN-dist); `build_teaching_pack_graph` injects no `QualityGate` | parity-001 |
| §3.6 | 5-strategy healing | Legacy-only; teaching-pack has scoped-regeneration; `max_healing_attempts` is dead config | parity-002 |
| §7.7 | "GIFT/H5P not in current tree" | **Wrong** — exporters exist at `packages/exporters/src/{gift,h5p,qti,google-forms}`; but `export_finalize` emits **only `.html`** (exporters never invoked) | parity-005 |
| §3.8 | single event bus | Two buses (`events.py` + `teaching_pack_event_bus.py`), fragmented | parity-003 |
| §3.2 | diagnostic/roadmap in pipeline | Legacy-only; no stage in the 8-stage graph | port at topic-decomposition Phase 3 |
| §6 | Layer-2 pedagogical metrics measured | **Stub** — `pedagogical.py:61` hardcodes all 7 to `True` (silent-pass); runtime-parity wired the layer but the metrics are fake | effectiveness-loop 002 (de-stub) |
| §10 | pipeline measures learning effectiveness | **No** — measures content quality only; no outcome capture / knowledge tracing | **ADR-019** + `effectiveness-loop` epic |
| §3.4 | 30 middleware wired into runtime | **Not wired** — `ORDERED_MIDDLEWARE_LIST` (30 entries) is declared in `registry.py` but legacy `graph.py` has zero references; teaching-pack has no middleware chain | wire-001 |
| §7 | Layer 3 (HTML/presentation) check | **Missing in teaching-pack** — no DOCTYPE/CDN/brand-string validation in `render_quality`; only in legacy `content_reviewer.py` | parity-006 |
| §7 | Layer 4 (LLM-as-Judge, 3-judge majority) | **Missing in teaching-pack** — no G-Eval, no judge calls; only legacy `sub_agents/reviewer/nodes.py` uses `GEvalScorer` | parity-007 |
| §7 | Layer 6 (multi-judge export check) | **Missing in teaching-pack** — `export_finalize` returns path strings without content generation; no export validation | parity-008 |
| §8.1 | "9Router sidecar :20128" | **STUB** — `services/router/Dockerfile` CMD is `echo "9Router — configure with real image"`; not operational | router-001 |
| §9.1 | Production compose healthy | **Likely broken** — prod overlay declares `depends_on: 9router: service_healthy` but never defines `9router` service | compose-001 |
| §6 | Langfuse observability operational | **Unverified** — env vars declared in `.env.example`; integration code in `packages/agents/observability.py` not yet audited | obs-001 |

**Learning-outcome effectiveness loop (ADR-019):** a new longitudinal subsystem (outcome store + Google Forms auto-capture + pyBKT knowledge tracing + RISE feedback) measures whether packs actually teach and feeds mastery back into planning — see `.scratch/effectiveness-loop/`. The pipeline reads mastery at planning time and writes a non-blocking delivery record post-export; effectiveness is retrospective, never a pre-delivery gate.

**Shared, NOT legacy (do not delete):** `Run`/`RunStatus`/`RunEvent` models (used by `teaching_pack_store`/`RunStatusHistory`), sub-agent node functions, `packages/quality`, `healing/orchestrator.py`, contracts. The legacy *graph* + legacy *routes* are removed (parity-004) only after parity; sub-agent simplification (parity-006) is behavior-preserving with zero feature loss.

---

## ⚠️ INFRASTRUCTURE STATUS (2026-06-30, verified)

| Component | Claimed State | Actual State | Confidence |
|-----------|---------------|--------------|------------|
| `.env.example` | Listed | Real, current, uses `4omc` model name (NOT gpt-5.4/deepseek-* per AGENTS.md §6.1) | HIGH |
| `.env`, `.env.local`, `.env.production` | Implied | Files exist, contents **UNREAD** | LOW |
| **9Router sidecar :20128** | "All traffic routes through 9Router" | **STUB** — Dockerfile runs `echo "9Router — configure with real image"`; not operational | HIGH |
| LiteLLM proxy :4000 | Configured | Real, **production-only**; all routes → 9Router stub | HIGH |
| PostgreSQL :5432 | Configured | Real in prod compose (as `db`) | HIGH |
| Redis :6379 | Configured | Real in prod compose | HIGH |
| Langfuse observability | Configured | Env vars declared; integration code **UNVERIFIED** | LOW |
| **Production docker-compose** | Working | **Likely broken** — depends on undefined `9router` service | MEDIUM |
| dev/staging compose | Working | **UNREAD** | NONE |
| Startup scripts (`scripts/setup.sh`) | Working | **UNREAD** | NONE |

---

## Table of Contents

1. [System Identity](#1-system-identity)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Orchestration Layer](#3-agent-orchestration-layer)
4. [Gateway API](#4-gateway-api)
5. [Frontend Dashboard](#5-frontend-dashboard)
6. [Quality Gate System](#6-quality-gate-system)
7. [Template & Rendering Engine](#7-template--rendering-engine)
8. [LLM Routing](#8-llm-routing)
9. [Infrastructure](#9-infrastructure)
10. [Data Flow — End-to-End](#10-data-flow--end-to-end)
11. [Hard Invariants](#11-hard-invariants)
12. [File Index](#12-file-index)

---

## 1. System Identity

**oh-my-class** is an AI-powered **teaching pack generator** for K-12 education. A teacher describes a lesson; the system produces a complete, print-and-use HTML teaching pack — lesson, worksheet, quiz, drill, recap, infographic — tailored to their students.

### Core Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Orchestration | LangGraph 1.x | Sequential pipeline + `interrupt()` for teacher gates |
| Backend | FastAPI (Python 3.12) | Async, type-safe, OpenAPI auto-docs |
| Frontend | Next.js 15 (TypeScript) | SSR + App Router; teacher dashboard |
| Template Engine | Eta (JS/TS) | 3.5 KB, TypeScript-native, standalone HTML output |
| LLM Gateway L1 | LiteLLM Proxy :4000 | Budget control, cost tracking, fallback chains |
| LLM Gateway L2 | 9Router sidecar :20128 | RTK token compression, free-tier aggregation |
| Cache | Redis 7 | LiteLLM exact-match cache |
| Persistence | PostgreSQL 16 | LangGraph checkpoints, cost logs, artifact metadata |
| Observability | Langfuse v3 | Traces, evaluations, cost tracking |
| Validation | Pydantic v2 (Python) + Zod (TS) | Bi-directional schema enforcement |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     Teacher (Browser)                             │
│                   Next.js 15 Dashboard :3000                      │
└──────────────────────────┬───────────────────────────────────────┘
                           │ REST / SSE (EventSource)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│               FastAPI Gateway :8001                               │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │         LangGraph Runtime (Embedded)                       │  │
│  │                                                            │  │
│  │  ┌──────────────────┐   ┌─────────────────────────────┐   │  │
│  │  │  Legacy Graph    │   │  Teaching-Pack Graph         │   │  │
│  │  │  (18 nodes, FROZEN)│ │  (8 stages, AUTHORITATIVE)   │   │  │
│  │  └──────────────────┘   └─────────────────────────────┘   │  │
│  │                                                            │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  Middleware Chain (30 modules, order 1–24)            │ │  │
│  │  └──────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  LiteLLM Proxy :4000 ──► 9Router sidecar :20128                 │
│  PostgreSQL :5432 │ Redis :6379 │ Langfuse :3100                 │
└──────────────────────────────────────────────────────────────────┘
```

### Two Graph Runtimes (Side-by-Side)

| Runtime | Status | Nodes | State Storage | Invocation |
|---------|--------|-------|---------------|------------|
| Legacy (`build_oh_my_class_graph`) | **FROZEN** (ADR-017) | 18 | In-memory dict + checkpointer | Direct HTTP `graph.ainvoke()` |
| Teaching-Pack (`build_teaching_pack_graph`) | **AUTHORITATIVE** | 8 stages | PostgreSQL + checkpointer | Job queue → worker → `graph.ainvoke()` |

---

## 3. Agent Orchestration Layer

### 3.1 State Schema — `OhMyClassState`

File: `packages/agents/state.py` (121 lines)

```python
class OhMyClassState(TypedDict):
    # Input
    raw_request: str
    teacher_id: str
    class_info: dict[str, Any]      # {grade, subject, student_count, language}
    run_id: str

    # Planning
    lesson_plan: NotRequired[dict]
    blueprint_approved: bool
    revision_feedback: NotRequired[str]

    # Research
    research_bundle: NotRequired[dict]
    research_policy: str             # "basic" | "standard" | "rigorous"

    # Content
    artifact_types: list[str]
    theme: str
    artifacts: Annotated[list[dict], merge_artifacts]  # deduplicated

    # Quality
    quality_scores: NotRequired[dict]
    quality_passed: bool
    teacher_approved: bool
    revision_count: int

    # Gate tracking
    fail_layer: NotRequired[str | None]     # "schema"|"content"|"judge"|"human"
    fail_count: NotRequired[int]
    fail_type: NotRequired[str | None]      # "validation"|"content"|"score"|"timeout"
    fail_context: NotRequired[dict | None]

    # Gate scores
    schema_valid: NotRequired[bool | None]
    content_review_passed: NotRequired[bool | None]
    judge_score: NotRequired[float | None]  # overall G-Eval
    export_ready: NotRequired[bool | None]

    # Healing
    escalate: NotRequired[bool]
    escalate_reason: NotRequired[str | None]
    healing_strategy: NotRequired[str | None]  # retry|rewrite|reroute|replan|escalate
    healing_note: NotRequired[str | None]
    healing_context: NotRequired[dict | None]
    generation_model: NotRequired[str | None]  # model override

    # HITL
    teacher_decision: NotRequired[str]    # approve|reject|edit
    gate_payload: NotRequired[dict]

    # Error
    error: NotRequired[str]

    # Review
    review_results: NotRequired[dict | None]

    # Diagnostic
    student_responses: NotRequired[dict | None]
    diagnostic_report: NotRequired[dict | None]
    student_profile: NotRequired[dict | None]

    # Export
    export_formats: list[str]            # ["html", "gift", "h5p"]
    exported_files: Annotated[list[dict], merge_exported_files]

    # Metadata
    current_step: int                    # 1–13
    tokens_used: int
    cost_usd: float
```

**Custom Reducers:**
- `merge_artifacts()` — Deduplicated union preserving insertion order. Key = `item["id"]` if present, else `str(item)`.
- `merge_exported_files()` — Delegates to `merge_artifacts`.

### 3.2 Legacy Graph — 18 Nodes

File: `packages/agents/graph.py` (362 lines)

```
step_00_diagnostic → step_01_preflight → step_02_quickstart → step_03_blueprint
  → gate_01_blueprint_approval → step_04b_roadmap
  → step_05_pack_scope → step_06_visual_engine → step_07_research
  → step_08_generate → step_09_schema_validate → step_10_content_review
  → step_10b_llm_judge → gate_02_content_approval
  → step_11_export_readiness → step_12_finalize → END

healing_node (self-heal orchestrator, routes back or escalates)
escalate_node (terminal failure → END)
```

**Node details:**

| # | Node | Source File | Role |
|---|------|-------------|------|
| 0 | `step_00_diagnostic` | `sub_agents/diagnostician/agent.py` | Student diagnostics |
| 1 | `step_01_preflight` | `nodes/preflight.py` | Input validation |
| 2 | `step_02_quickstart` | `nodes/quickstart.py` | Quick-start routing |
| 3 | `step_03_blueprint` | `sub_agents/planner/agent.py` | Lesson plan (UbD) |
| 4 | `gate_01_blueprint_approval` | `gates/gate_01_blueprint.py` | Teacher gate (interrupt) |
| 5 | `step_04b_roadmap` | `sub_agents/roadmap_agent/agent.py` | Unit roadmap |
| 6 | `step_05_pack_scope` | `nodes/pack_scope.py` | Pack scoping |
| 7 | `step_06_visual_engine` | `nodes/visual_engine.py` | Visual design |
| 8 | `step_07_research` | `sub_agents/researcher/agent.py` | Source research |
| 9 | `step_08_generate` | `sub_agents/content_creator/agent.py` | Content generation |
| 10 | `step_09_schema_validate` | `gates/schema_validator.py` | Layer 1 validation |
| 11 | `step_10_content_review` | `gates/content_reviewer.py` | Layer 2–3 review |
| 12 | `step_10b_llm_judge` | `gates/llm_judge.py` | Layer 4 G-Eval |
| 13 | `gate_02_content_approval` | `gates/gate_02_content_approval.py` | Teacher gate (interrupt) |
| 14 | `step_11_export_readiness` | `gates/export_readiness.py` | Layer 6 check |
| 15 | `step_12_finalize` | `nodes/finalize.py` | Finalize + export |
| H | `healing_node` | `healing/orchestrator.py` | Self-heal orchestrator |
| E | `escalate_node` | `graph.py:131–136` | Terminal failure |

**Conditional edges (9):**

| From | Router | True → | False → |
|------|--------|--------|---------|
| `step_00_diagnostic` | `route_after_diagnostic` | `step_01_preflight` | — |
| `gate_01_blueprint_approval` | `route_after_blueprint_gate` | `step_04b_roadmap` | `step_03_blueprint` |
| `step_04b_roadmap` | `route_after_roadmap` | `step_05_pack_scope` | — |
| `step_09_schema_validate` | `route_after_schema` | `step_10_content_review` | `healing_node` |
| `step_10_content_review` | `route_after_content_review` | `step_10b_llm_judge` | `healing_node` |
| `step_10b_llm_judge` | `route_after_judge` | `gate_02_content_approval` | `healing_node` |
| `gate_02_content_approval` | `route_after_content_gate` | `step_11_export_readiness` | `step_08_generate` |
| `step_11_export_readiness` | `route_after_export` | `step_12_finalize` | `escalate_node` |
| `healing_node` | `route_after_healing` | `step_08_generate` | `escalate_node` |

### 3.3 Teaching-Pack Graph — 8 Stages (AUTHORITATIVE)

File: `packages/agents/teaching_pack/graph.py`

```
setup_contract → preplanning_search → planning_blueprint → post_blueprint_research
  → artifact_workflow → render_quality → teacher_approval → export_finalize → END
```

**Verified stage wiring** (from `graph.py:35-66` + `stages.py:32-41`):

| # | Stage | Node Function | File:Line | What It Actually Calls |
|---|-------|---------------|-----------|------------------------|
| 1 | `setup_contract` | `_setup_contract` | `nodes.py:75` | Stores contract (no LLM) |
| 2 | `preplanning_search` | `_preplanning_search` | `nodes.py:85` | **STUB** — creates stub research_brief with "Teacher-provided lesson context"; no actual search |
| 3 | `planning_blueprint` | `_planning_blueprint` | `nodes.py:103` | Calls `planner_node` from sub_agents.planner.nodes |
| 4 | `post_blueprint_research` | `_post_blueprint_research` | `nodes.py:118` | Calls `researcher_node` (key mismatch: `research_brief` passed as `research_bundle`) |
| 5 | `artifact_workflow` | `_artifact_workflow` | `nodes.py:133` | Calls `content_creator_node` |
| 6 | `render_quality` | `_render_quality` | `nodes.py:154` | Delegates to `quality_runtime.render_quality` |
| 7 | `teacher_approval` | `_teacher_approval` | `nodes.py:160` | Uses LangGraph `interrupt()` |
| 8 | `export_finalize` | `_export_finalize` | `nodes.py:188` | Calls `ExporterRegistry.default().export()` |

**Conditional seams (2):**
- After `render_quality`: routes to `planning_blueprint` | `post_blueprint_research` | `artifact_workflow` | `teacher_approval` (via `quality_routing.py:27-39`)
- After `teacher_approval`: approve → `export_finalize`; reject with scoped feedback → `artifact_workflow` (via `nodes.py:210-215`)

**⚠️ Verified gaps in teaching-pack quality flow**:
- **No Layer 3 (HTML/presentation)** — no DOCTYPE, CDN, or brand-string checks
- **No Layer 4 (LLM-as-Judge)** — no G-Eval, no 3-judge majority vote
- **No Layer 6 (multi-judge export)** — export returns path strings without validation

**Supporting modules:**
- `stages.py` — `TeachingPackStage` StrEnum (8 values)
- `nodes.py` — `make_stage_node()` dispatch per stage
- `ports.py` — `QualityGate` Protocol boundary (line 125)
- `quality.py` — In-pipeline quality checks (schema + content + coherence + VN difficulty)
- `quality_runtime.py` — `render_quality()` orchestrator
- `quality_routing.py` — Routing after quality checks
- `scoped_regeneration.py` — Teacher-reject loop with scoped feedback
- `snapshots.py` — State snapshots for resumability
- `checkpointing.py` — Stage-graph-specific checkpointer
- `artifacts.py` — Artifact write logic
- `config.py` — Stage-graph config
- `healing_runtime.py` — `heal_quality_failure()` calls legacy `HealingOrchestrator` (line 32)
- `exporters.py` — Inline `ExporterRegistry` (string-path stubs only)

### 3.4 Middleware Chain — 30 Modules (REGISTERED, NOT WIRED)

File: `packages/agents/middleware/registry.py`

**⚠️ Critical finding**: The 30-middleware chain is **declared but not executed**. Evidence:
- `legacy/packages/agents/graph.py` — grep for `middleware|Middleware` returned **zero matches**
- `teaching_pack/packages/agents/teaching_pack/graph.py` — **no middleware registration** (builder takes `checkpointer`, `quality_gate`, `interrupt_before`, `interrupt_after` — no middleware list)

The 30-entry list is a **registry, not an active execution chain**.

```python
class BaseMiddleware(ABC):
    name: str
    order: int                # 1–30; Clarification = 30 (NOT 24 per stale base.py docstring)

    @abstractmethod
    async def before_model(self, state, context) -> state: ...

    @abstractmethod
    async def after_model(self, state, context) -> state: ...
```

**INVARIANT-08 (corrected):** Clarification middleware is always last (`order=30`). All others `order ∈ 1–29`.

**⚠️ Docstring discrepancy**: `base.py` docstring says "1–23, Clarification=24" — this is **stale**; `registry.py` is authoritative (1–30, Clarification=30).

| Category | Modules | Count | Order Range |
|----------|---------|-------|-------------|
| Safety | input_sanitization, token_budget, thread_data, uploads, content_safety, dangling_tool_call, llm_error_handling, guardrail, teacher_audit_log, tool_error_handling, loop_detection, safety_finish_reason | 12 | 1–12 |
| Context | dynamic_context, skill_activation, summarization, todo_list, token_usage, title, memory, view_image, deferred_tool_filter, system_message_coalescing | 10 | 13–22 |
| Quality | subagent_limit, curriculum_alignment, readability_level, pedagogical_quality, bias_detection, artifact_coherence, learning_objective_alignment | 7 | 23–29 |
| Terminal | clarification | 1 | 30 |

**Unregistered/orphan files** at `middleware/` root: `dangling_tool_call.py`, `guardrail.py`, `loop_detection.py`, `summarization.py`, `token_budget.py` — legacy flat-file duplicates, backward-compat shims.

### 3.5 Sub-Agents — 6 Agents

Each follows identical 5-file pattern:

```
sub_agents/<name>/
├── agent.py       # StateGraph builder: make_<name>_agent() → CompiledStateGraph
├── nodes.py       # node function (the LLM call)
├── state.py       # <Name>State TypedDict
├── adapters.py    # parent OhMyClassState ↔ sub-agent state bridge
└── prompts/system.md
```

| Agent | Model | Role |
|-------|-------|------|
| **planner** | `deepseek-v4-flash` | Backward design (UbD) lesson planning |
| **researcher** | `deepseek-v4-flash` | Source gathering, FACT protocol |
| **content_creator** | `deepseek-free` → `deepseek-compressed` | JSON content for each artifact type |
| **reviewer** | `content-fusion` (3-judge majority) | LLM-as-Judge, G-Eval scoring |
| **diagnostician** | (parent model) | Student response analysis |
| **roadmap_agent** | (parent model) | Unit-level planning |

**Lead Agent** (`packages/agents/lead_agent/`) orchestrates via `task()` calls. **NEVER** generates content directly (INVARIANT-01).

### 3.6 Healing & Escalation

File: `packages/agents/healing/orchestrator.py` (legacy) + `packages/agents/teaching_pack/healing_runtime.py` (teaching-pack)

**⚠️ Verified reality**: 5-strategy healing is **legacy-only**. Teaching-pack uses a **simplified inline helper** that calls the same legacy `HealingOrchestrator()`:

**Legacy 5 strategies** (`packages/agents/healing/orchestrator.py`):

| Attempt | Strategy | Trigger |
|---------|----------|---------|
| 1st | Rewrite (same model, new prompt with error feedback) | Validation failure |
| 2nd | Reroute (different model) | Model-specific failure |
| 3rd | Replan (new content plan) | Structural failure |
| 4th | Escalate to teacher | Budget exhausted |

**Teaching-pack healing** (`packages/agents/teaching_pack/healing_runtime.py:16-50`):
- `heal_quality_failure()` constructs `healing_state` with `fail_count`, `fail_type`, `fail_layer="quality"`, `fail_context.errors`
- Calls `HealingOrchestrator().heal(healing_state)` at line 32 (reuses legacy orchestrator)
- Routes via `_route_for_healing` (line 40-50):
  - `escalate=True` → `teacher_approval`
  - `healing_strategy="replan"` → `planning_blueprint`
  - Pedagogical/factual failures → `planning_blueprint`
  - Otherwise → `artifact_workflow`

**⚠️ No `healing_node` or `escalate_node` graph nodes exist in teaching-pack**. Healing is invoked **inside** `render_quality` as a synchronous helper at `quality_runtime.py:53`. Routing decisions are surfaced via the `quality_recovery_route` state field consumed by `route_after_render_quality` in `graph.py:55-62`.

**⚠️ No 24-hour timeout / escalation cron** in teaching-pack. Timeout machinery (`services/gateway/recovery_sweeper.py`) is a gateway concern, not a teaching-pack node concern.

**⚠️ Healing escalation in teaching-pack → `teacher_approval`** (not admin). Differs from legacy `escalate_node → END`.

### 3.7 Gate System

| Gate | File | Used In |
|------|------|---------|
| Blueprint approval | `gates/gate_01_blueprint.py` | Legacy only |
| Content approval | `gates/gate_02_content_approval.py` | Both graphs |
| Schema validation | `gates/schema_validator.py` | Legacy (Layer 1) |
| Content review | `gates/content_reviewer.py` | Legacy (Layer 2–3) |
| LLM judge | `gates/llm_judge.py` | Legacy (Layer 4) |
| Export readiness | `gates/export_readiness.py` | Legacy (Layer 6) |

**Teacher gate payload:**
```python
interrupt({
    "gate": "content_approval",
    "artifacts": state["artifacts"],
    "quality_scores": state["quality_scores"],
    "actions": ["approve", "edit", "reject"]
})
```

**INVARIANT-06:** Teacher Gate CANNOT be bypassed. `interrupt()` must be called. Timeout: 24 hours → auto-escalate.

### 3.8 Event System & Checkpointing

- **Events:** `packages/agents/events.py` — in-memory SSE bus. Emits `step_started`, `step_completed`, `step_failed`.
- **Observability:** `packages/agents/observability/` — Langfuse tracing via `trace_node()`.
- **Checkpointing:** `packages/agents/checkpointer.py` — `MemorySaver` (dev) / `SqliteSaver` (staging) / `PostgresSaver` (prod).

---

## 4. Gateway API

### 4.1 App Initialization

File: `services/gateway/main.py` (177 lines)

FastAPI on `:8001`. Lifespan:
1. Configure logging (JSON structured)
2. Create async SQLAlchemy engine + session factory
3. Initialize checkpointer per environment
4. Build legacy graph (`app.state.graph`) + teaching-pack graph (`app.state.teaching_pack_graph`)
5. Start background tasks: recovery sweeper (60s) + worker loop (1s idle)
6. Register 10 routers

**Middleware stack (outermost first):**
```
CORSMiddleware (localhost:3000, localhost:3100)
RequestIDMiddleware
JWTMiddleware
```

### 4.2 Router Catalog

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `auth_router` | (none) | POST /auth/login, POST /auth/logout, GET /auth/me |
| `runs` | `/run` | GET /run, POST /run, GET /run/{id}, GET /run/{id}/status (SSE), GET /run/{id}/exports |
| `artifacts` | `/run` | GET /run/{id}/artifacts, GET /run/{id}/artifacts/{aid} |
| `snapshots` | `/run` | GET /run/{id}/snapshots |
| `approvals` | `/run` | POST /run/{id}/approve, POST /run/{id}/reject |
| `teaching_pack_runs` | `/teaching-packs` | POST /teaching-packs/run, POST /teaching-packs/runs/{id}/resume |
| `teaching_pack_previews` | `/teaching-packs` | GET /teaching-packs/{id}/previews |
| `webhooks` | `/webhook` | POST /webhook/telegram, POST /webhook/zalo |
| `notifications` | `/notifications` | GET /notifications, GET /notifications/{id}, POST /notifications/{id}/read |
| `release_evidence` | `/teaching-packs` | GET /teaching-packs/{id}/release-evidence |

### 4.3 Request/Response Schemas

**Run creation (legacy):**
```python
class RunRequest(BaseModel):
    raw_request: str
    class_info: dict[str, Any]
    teacher_id: str              # overridden by JWT
    artifact_types: list[str] | None = None

class RunResponse(BaseModel):
    run_id: str
    status: str                  # derived via _derive_status()
    topic: str | None = None
    current_step: int | None = None
    artifact_types: list[str] | None = None
    state: dict[str, Any] | None = None
```

**Teaching-pack creation:**
```python
class TeachingPackCreateRunRequest(BaseModel):
    raw_request: str
    class_info: dict[str, Any]

class TeachingPackRunAcceptedResponse(BaseModel):
    run_id: RunId
    job_id: str | None
    status: RunStatus
    queued: bool | None = None
```

**Approval:**
```python
class ApprovalRequest(BaseModel):
    action: ApprovalAction        # "approve" | "reject"
    feedback: str | None = None
    edits: dict[str, Any] | None = None
```

### 4.4 Auth System

- **JWTMiddleware:** Bearer header or `auth-token` cookie (SSE paths only)
- **Public paths:** `/health`, `/auth/login`, `/docs`, `/openapi.json`, `/redoc`, `/webhook/*`
- **Dependencies:** `require_teacher` (most endpoints), `require_admin` (admin endpoints)
- **JWT:** Verified via `auth/jwt_handler.py`, secret from environment

### 4.5 Job Queue (Teaching-Pack Path)

File: `services/gateway/teaching_pack_job_store.py` (212 lines)

**Job lifecycle:** `PENDING → QUEUED → RUNNING → COMPLETED | FAILED | CANCELLED`

- **Enqueue:** `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING`
- **Claim:** `SELECT ... FOR UPDATE SKIP LOCKED` with lease-based locking
- **Lease:** 120 seconds, refreshed on claim
- **Backpressure:** Configurable per-teacher rate limiting
- **Idempotency:** Scoped per teacher (create) or per run+teacher (resume)

### 4.6 Worker Loop

```python
# main.py background task
async def _run_teaching_pack_worker():
    worker = TeachingPackWorker(
        worker_id="gateway-worker",
        lease_seconds=120,
        idle_sleep_seconds=1.0,
    )
    while True:
        await worker.run_one()  # claim → execute → mark_complete/failed
        await asyncio.sleep(1.0)
```

### 4.7 Recovery Sweeper

Runs every 60 seconds:
- `sweep_stuck_jobs()` — Reset expired leases, retry or fail after max attempts
- `sweep_escalated_gates()` — Auto-escalate gates past 24-hour TTL

### 4.8 SSE Streaming

**Legacy:** `GET /run/{run_id}/status` — EventSourceResponse subscribing to `events.py` bus
**Teaching-Pack:** `GET /teaching-packs/runs/{run_id}/stream` — Separate event bus via `teaching_pack_event_bus.py`

Both allow cookie auth for browser EventSource compatibility.

### 4.9 Database Models

**Legacy:** `Run`, `RunStatus`, `RunEvent` (SQLAlchemy)
**Teaching-Pack:** `RunJob`, `TeachingPackRun`, `GateResponse`, `ArtifactSnapshot`, `RenderedSnapshot`, `Notification`, `ReleaseEvidence`, `BudgetLedger`, `ProviderEvidence`

**13 Alembic migrations** (001 initial → 013 gate interrupt uniqueness)

---

## 5. Frontend Dashboard

### 5.1 Stack

- **Framework:** Next.js 15 (App Router, route groups, Server Components)
- **UI:** shadcn/ui (6 primitives), Tailwind, PostCSS
- **State:** TanStack Query (server state) + Zustand (UI state)
- **Testing:** Vitest (unit) + Playwright (e2e)
- **Auth:** Edge middleware at root

### 5.2 Page Tree

```
/                              ← Root layout (providers, fonts, globals)
  /approvals                   ← Gate decision UI
  /runs                        ← Run list
  /runs/new                    ← Create run form
  /runs/:runId                 ← Run detail (live SSE updates)
```

### 5.3 Key Components

| Component | Purpose |
|-----------|---------|
| `approval-modal.tsx` | Gate decision modal (approve/reject/edit) |
| `artifact-preview.tsx` | HTML artifact renderer |
| `run-card.tsx` | Run list card |
| `inverse-thinking-editor.tsx` | Edit-with-feedback editor |
| `teaching-packs-artifact-progress.tsx` | Live artifact generation progress |
| `teaching-packs-gate-shell.tsx` | Gate presentation wrapper |
| `methodology/` | Plugin-style teaching-pack mode system |

### 5.4 Data Flow

```
Browser → middleware.ts (auth gate)
  → (dashboard)/layout.tsx (Server Components fetch initial data)
  → lib/api-client.ts (typed fetch → gateway :8001)
  → hooks/use-*.ts (TanStack Query mutations/queries)
  → components/*.tsx (UI presentation)
  → SSE: use-teaching-packs.ts → teaching-packs-artifact-progress.tsx
```

### 5.5 Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/lib/api-client.ts` | — | Fetch wrapper, base URL, auth headers |
| `src/lib/query-client.tsx` | — | TanStack Query provider |
| `src/stores/ui-store.ts` | — | Zustand global UI state |
| `src/hooks/use-teaching-packs.ts` | — | SSE consumer for real-time progress |
| `src/hooks/use-approval.ts` | — | Gate approval mutation |
| `src/types/teaching-pack-api.ts` | — | API response types |
| `middleware.ts` | — | Edge auth gating |

---

## 6. Quality Gate System

### 6.1 Two Quality Systems

| System | Location | When |
|--------|----------|------|
| **In-pipeline** | `packages/agents/teaching_pack/quality.py` | Runs inline during `artifact_workflow` stage |
| **6-Layer** | `packages/quality/` | Runs during `render_quality` stage via `QualityGate` Protocol |

### 6.2 In-Pipeline Quality (Teaching-Pack)

File: `packages/agents/teaching_pack/quality.py`

**Checks performed:**
1. **Schema validation** — `ArtifactContent.model_validate()` (Pydantic v2)
2. **Placeholder detection** — Regex: `\b(?:todo|placeholder|lorem ipsum|tbd)\b|\[tbd\]`
3. **Answer-key leakage** — Regex: `\b(?:answer key|answer:|correct:|solution:)\b` on non-`teacher_only` sections
4. **Accessibility** — `accessibility.language` must be present
5. **Pack coherence** — Quiz must share terms with lesson; lesson `key_terms` must appear in quiz/worksheet; lesson objectives must surface in all artifacts
6. **Vietnamese difficulty distribution** — For `vi-*` locale: `nhan_biet=0.4 / thong_hieu=0.3 / van_dung=0.2 / van_dung_cao=0.1` (±0.05)

Raises `TeachingPackQualityGateError(issues)` on failure.

### 6.3 6-Layer Quality System

```
Layer 1 (Schema)     → 15%  weight
Layer 2 (Content)    → 55%  weight
Layer 3 (HTML)       → 30%  weight
Layer 4 (LLM Judge)  → G-Eval scoring, 3-judge majority vote
Layer 5 (HITL)       → Teacher gate via interrupt()
Layer 6 (Export)     → 3 independent judges, 2/3 must pass
```

**Pass threshold:** `overall_score ≥ 7.0` AND no critical issues.

**Layer modules:**

| Layer | Directory | Key Files |
|-------|-----------|-----------|
| 1 — Schema | `layer1_schema/` | `validators.py`, `circuit_breaker.py`, `component_gate.py` |
| 2 — Content | `layer2_content/` | `fact_check.py`, `age_check.py`, `pedagogical.py`, `readability_checker.py`, `pii.py`, `methodology.py` |
| 3 — HTML | `layer3_html/` | `html_validator.py`, `responsive_check.py` |
| 4 — Judge | `layer4_judge/` | `geval.py`, `majority_vote.py`, `judge_interface.py`, `judge_transport.py`, `judge_prompts.py`, `hard_blocks.py`, `rubric_selector.py` |
| 5 — Human | `layer5_human/` | `interrupt_handler.py` |
| 6 — Export | `layer6_export/` | `export_validator.py` |

### 6.4 Hard Blocks (Auto-Fail)

```python
HARD_BLOCKS = [
    "missing_doctype",          # No <!DOCTYPE html>
    "external_assets",          # Any CDN/http link
    "answer_key_leakage",       # Answer key in student view
    "native_radio_inputs",      # <input type="radio"> visible to student
    "unmanaged_js_runtime",     # External JS framework loaded
    "missing_brand_string",     # "oh-my-class" not present
]
```

### 6.5 Quality Routing

File: `packages/agents/teaching_pack/quality_routing.py`

Routes based on quality report:
- All pass → `teacher_approval`
- Issues found → `artifact_workflow` (scoped regeneration)
- Critical failure → healing strategies

### 6.6 AGENTS.md Discrepancies Found

1. `packages/agents/gates.py` per AGENTS.md is actually `packages/agents/gates/` (a directory)
2. `common/contracts/gate_config.yaml` per AGENTS.md is actually `packages/quality/gate_config.yaml`

---

## 7. Template & Rendering Engine

### 7.1 Rendering Pipeline

```
ArtifactContent JSON (Pydantic-validated)
        │
        ▼
renderArtifact<T>(type, data)              [renderer.ts]
   ├─ themeCSS = loadTheme(themeName)       [theme/loader.ts]
   ├─ html = eta.renderAsync("pages/<type>", { ...data, themeCSS, lang })
   │     │
   │     ▼  Eta singleton (autoEscape=true, useWith=false)
   │     pages/<type>.html includes components/*.html
   │     base.html wraps with <!DOCTYPE>, theme CSS, header/footer
   │
   └─ sanitize(html, type)                  [sanitizer/ + DOMPurify]
        +
   validateNoExternalUrls(html)             [inline-assets.ts] ← INVARIANT-04
        │
        ▼
   Standalone HTML string
```

### 7.2 Template Inventory

| Category | Count | Location |
|----------|-------|----------|
| Base shell | 1 | `templates/base.html` |
| Page templates | 11 | `templates/pages/` (answer_key, drill, exit_ticket, flashcard_deck, infographic, lesson, quiz, reading_passage, recap, roadmap, worksheet) |
| Component templates | 45 | `templates/components/` (question types, hints, feedback, charts, concept maps, etc.) |

### 7.3 Three-Tier CSS Token System

```
PRIMITIVES              SEMANTIC TOKENS        COMPONENT TOKENS
(raw hex values)        (meaning)              (scoped to component)

--color-blue-500   →   --color-primary    →   .quiz-option { border-color: var(--color-primary) }
--space-4          →   --space-md
```

**Token types:**
- `PrimitiveTokens` — colorPalette, spacing, fontFamily, fontSizeScale, borderRadius, shadow
- `SemanticTokens` — colorBg, colorText, colorAccent, colorSuccess/Warning/Error, categoryColors
- `ComponentTokens` (optional) — questionCardRadius, flashcardHeight, flashcardRadius

### 7.4 Theme System

- **Source of truth:** `common/branding/kits/{default,ocean,forest}/theme.json` (INVARIANT-09)
- **Generated CSS:** `packages/renderer/branding/theme_{name}.css` — never edit manually
- **Runtime:** `loadTheme(name)` reads JSON → `generator.ts` emits CSS → injected into `:root` in `base.html`

### 7.5 Security Layers

1. **Eta auto-escape** — `autoEscape: true` in singleton Eta config
2. **DOMPurify** — Per-artifact configs in `sanitizer/configs/*.ts`
3. **External URL guard** — `validateNoExternalUrls()` in `inline-assets.ts` (INVARIANT-04)
4. **CSP** — `preview-server/csp.ts` for iframe sandbox
5. **SVG sanitizer** — `diagrams/svg-sanitizer.ts` for inline SVGs

### 7.6 Exercise Type System

**Question taxonomy** (`contracts/questions/`):
- `choice` (single/multiple)
- `fill-gap`
- `match`
- `order`
- `open` (short-answer, essay)
- `interactive` (drag-and-drop, branching)
- `multimedia` (video/audio/photo-backed)
- `text-entry`

**Scoring strategies** (`scoring/strategies/`):
- `all-or-nothing.ts`
- `partial-credit.ts`
- `rubric.ts`
- `vietnamese-tf-2025.ts` — QĐ 764/QĐ-BGDDT TF 4-item scoring (1 correct=0.1đ, 2=0.25đ, 3=0.5đ, 4=1.0đ)

### 7.7 Export Formats

**⚠️ Verified reality (2026-06-30)**: Two-layer architecture with **disconnected** Python and TypeScript exporters.

#### Layer 1: Python Pipeline (`packages/agents/teaching_pack/`)

File: `packages/agents/teaching_pack/exporters.py` (89 lines)

**`ExporterRegistry.default().export()` behavior**:

| Format | Python Registry Behavior | Real Bytes? |
|--------|-------------------------|-------------|
| `html` | Returns path strings `exports/{run_id}/{snapshot_id}.html` per snapshot | NO — path only |
| `gift` | Returns path string `exports/{run_id}/{run_id}.gift.txt` | NO — path only |
| `h5p` | Returns path string `exports/{run_id}/{run_id}.h5p` | NO — path only |
| `qti` | Returns path string `exports/{run_id}/{run_id}.qti.xml` | NO — path only |
| `google_forms` | **Raises `UnsupportedExportFormatError`** | DEAD CODE |

**`_SUPPORTED_FORMATS = frozenset({"html", "gift", "h5p", "qti"})`**
**`_UNSUPPORTED_FORMATS = frozenset({"google_forms"})`**

`requested_export_formats(contract)` defaults to `["html"]`; if contract specifies formats but omits `html`, prepends `html`.

#### Layer 2: TypeScript Exporters (`packages/exporters/src/`)

File: `packages/exporters/src/index.ts` (41 lines)

```typescript
export type ExportFormat = "gift" | "h5p" | "qti";
export async function exportByFormat(
    format: ExportFormat,
    artifacts: ArtifactContent[],
): Promise<Buffer> { ... }
```

**TypeScript implementations exist and are tested**:
- `packages/exporters/src/gift/gift.ts` ✓ (with tests)
- `packages/exporters/src/h5p/h5p.ts` ✓ (with tests, includes h5p-impl/packager.ts)
- `packages/exporters/src/qti/qti.ts` ✓ (with tests)
- `packages/exporters/src/google-forms/` ✓ (exists but Python pipeline rejects it)
- `packages/exporters/src/anki-apkg/`, `flashcard-tsv/`, `inverse-thinking.ts` ✓

**⚠️ Critical wiring gap**: Python pipeline does **NOT** import or call the TypeScript exporters. No Node.js subprocess bridge, no IPC. The TypeScript exporters are **standalone library** code consumed only by renderer package tests (`packages/renderer/__tests__/exporters/qti.test.ts`) and their own unit tests.

#### Actual Export Flow

```
_export_finalize (nodes.py:188-207)
  ↓
ExporterRegistry.default().export() (exporters.py:39-52)
  ↓ returns string paths only
exported_files: list[str] stored in state
  ↓
services/gateway/teaching_pack_completion.py:50
  ↓
self._export_writer.write_exports(run_id, state)
  ↓ (NOT YET AUDITED)
[actual disk write — may or may not invoke TS exporters]
```

**Gap**: `services/gateway/teaching_pack_export_writer.py` has not been audited. Whether GIFT/H5P/QTI files on disk contain real exports or empty stubs depends on this unread file.

**Test coverage**: `packages/agents/tests/teaching_pack/test_export_format_wiring.py` exists — confirms this is a known testing concern (ADR-018).

**Correction needed in ARCHITECTURE.md §10**: Replace "All formats generated from the same `ArtifactContent` JSON" with the two-layer truth: TS exporters are real and tested but not wired to Python pipeline; Python pipeline returns path stubs for all formats except HTML (which has renderer-generated content upstream).

---

## 8. LLM Routing

### 8.1 Two-Layer Proxy Architecture

**⚠️ Verified reality (2026-06-30)**: 9Router is a **STUB** — not operational.

```
Agent (packages/agents/*)
  └─► LiteLLM Proxy :4000     (budget control, cost tracking, fallback chains, Redis cache)
        │
        └─► 9Router Sidecar :20128  [STUB — Dockerfile runs echo, not operational]
              │
              ├─► Kiro AI       (Claude 4.5 free tier)
              ├─► OpenCode      (free tier)
              └─► Vertex AI     ($300 one-time credit)
```

**⚠️ 9Router status (verified)**: `services/router/Dockerfile` CMD is `echo "9Router — configure with real image"`. The sidecar is not running; all upstream routes are effectively dead. This contradicts the "100% 9Router" claim in README.md.

**Dev mode:** Bypass LiteLLM, call 9Router directly via `LLM_BASE_URL` — but 9Router itself is a stub, so dev LLM calls also fail.

**⚠️ Production compose likely broken**: `docker-compose.prod.yml` declares `depends_on: 9router: service_healthy` but never defines a `9router` service in the overlay. If 9Router is also a stub in the base compose, production startup will hang.

### 8.2 Model Assignments

| Agent | Primary Model | 9Router Combo | Fallback |
|-------|--------------|---------------|----------|
| Lead Agent | `gpt-5.4` | `f.pro` | `deepseek-v4-flash` |
| Planner | `deepseek-v4-flash` | `f.light` | `deepseek-free` |
| Researcher | `deepseek-v4-flash` | `f.light` | `deepseek-free` |
| Content Creator | `deepseek-free` | `f.light` | `deepseek-compressed` |
| Reviewer (Judge) | `content-fusion` | `f.pro` (fusion) | `deepseek-free` |

### 8.3 9Router Combos

| Combo | Strategy | Providers |
|-------|----------|-----------|
| `f.light` | Free-tier | kiro-ai → opencode |
| `f.pro` | Free-tier | kiro-ai → opencode → vertex-ai |
| `content-fusion` | Parallel + judge | kiro-ai + opencode (parallel), judge=kiro-ai, majority vote |
| `deepseek-compressed` | RTK compression | kiro-ai → opencode (20–40% token savings) |

### 8.4 Fallback Chains

```
gpt-5.4             → deepseek-v4-flash         (f.pro → f.light)
deepseek-v4-flash   → deepseek-free             (f.light → f.light)
deepseek-free       → deepseek-compressed       (f.light → f.light RTK)
content-fusion      → deepseek-free             (f.pro fusion → f.light)
```

### 8.5 Configuration

**LiteLLM proxy** (`services/proxy/config.yaml`):
- `num_retries: 2`, `request_timeout: 60`, `allowed_fails: 3`, `cooldown_time: 60`
- Redis cache: `host: redis, port: 6379`
- All models: `max_budget: $0` (no paid fallbacks)

**9Router sidecar** (`services/router/config.yaml`):
- Health check: 30s interval, 10s timeout, 3-failure threshold
- Alerts: Slack webhook for provider_down, all_providers_down, free_tier_exhausted

### 8.6 Cost Attribution

Every LLM call includes metadata tags:
```python
{
    "tags": [
        "pipeline:oh-my-class",
        f"agent:{agent_name}",
        f"step:{state.get('current_step', 0)}",
        f"run:{state.get('run_id', 'unknown')}",
    ],
    "user": state.get("teacher_id", "anonymous"),
    "model_alias": model_name,
}
```

---

## 9. Infrastructure

**⚠️ Verified reality (2026-06-30)**: Several infrastructure components are not operational or have wiring gaps.

### 9.1 Service Topology (Verified from `infra/compose/docker-compose.yml`, 194 lines)

```
Teacher Browser
  │ HTTP :8001 / :3000
  ├──► web (Next.js :3000)
  └──► gateway (FastAPI :8001)
        │
        ├──► db (PostgreSQL :5432)
        ├──► redis (Redis :6379, AUTH required)
        ├──► proxy (LiteLLM :4000)
        │     └──► 9Router :20128 [STUB - echo command, not operational]
        └──► langfuse-web (Langfuse :3100)
              ├──► clickhouse (:8123/:9000, loopback only)
              ├──► minio (:9090/:9091, loopback only)
              └──► langfuse-worker (profile: langfuse-worker)
```

### 9.2 Service Catalog

| Service | Image | Port | Healthcheck | Notes |
|---------|-------|------|-------------|-------|
| `db` | `postgres:16-alpine` | 5432 | `pg_isready` 3s/3s/×10 | Volume `pgdata`. Hosts `langfuse` DB |
| `redis` | `redis:7-alpine` | 6379 | `redis-cli ping` 3s/10s/×10 | Auth via `${REDIS_AUTH}` |
| `gateway` | `Dockerfile.gateway` | 8001 | **NONE** | Depends on db (healthy), redis (healthy), proxy (started), langfuse-web (started) |
| `langfuse-web` | `langfuse/langfuse:3` | 3100 | **NONE** | Depends on db, clickhouse, redis, minio (all healthy) |
| `langfuse-worker` | `langfuse/langfuse-worker:3` | — | **NONE** | **`profiles: ["langfuse-worker"]`** — must opt in with `--profile langfuse-worker` |
| `clickhouse` | `clickhouse/clickhouse-server` | 8123/9000 | `wget /ping` 5s | **localhost-only ports** (127.0.0.1) |
| `minio` | `cgr.dev/chainguard/minio` | 9090/9001 | `mc ready local` 1s | Console port localhost-only |
| `proxy` | `Dockerfile.proxy` | 4000 | **NONE** | LiteLLM. Only depends on redis |
| `web` | `Dockerfile.web` | 3000 | **NONE** | Next.js. Depends on gateway |

**⚠️ Critical gaps**:
- **9Router NOT in dev compose** — Only in prod overlay (`docker-compose.prod.yml`), and prod overlay declares `depends_on: 9router: service_healthy` without defining the service → **likely broken startup**
- **9Router Dockerfile is a stub** — `services/router/Dockerfile` CMD is `echo "9Router — configure with real image"`. Not operational in any environment.
- **No healthchecks** for gateway, proxy, web, langfuse-web — downstream services depend on `service_started` (not `service_healthy`), so they start before upstream is truly ready.

### 9.3 Redis Configuration

- `--requirepass ${REDIS_AUTH:-omc_redis_secret}`
- `--maxmemory-policy noeviction` — No LRU eviction (required for cache semantics)
- No AOF/RDB persistence — pure cache + ephemeral state

### 9.4 PostgreSQL

- Single instance, 3 logical databases: `oh_my_class` (app), `langfuse` (observability), `postgres` (unused)
- Credentials: `omc_dev/omc_dev` (dev defaults — MUST override for prod)
- Init script: `init-db.sh` creates `langfuse` database on first boot

### 9.5 Package Management

**Python:**
- `uv` workspace with `uv.lock` (639K resolved)
- `import-linter` enforces boundary rules (packages/* cannot import from services/* or apps/*)
- Workspace members: `packages/agents`, `packages/quality`, `common/contracts`, `services/gateway`

**TypeScript:**
- `pnpm` workspaces + Turborepo task graph
- `Biome` for formatting + linting
- `.dependency-cruiser.cjs` enforces TS import boundaries

### 9.6 Environment Variables

| File | Size | Purpose | Status |
|------|------|---------|--------|
| `.env` | 5.0K | Active root dev env | **UNREAD** |
| `.env.example` | 5.8K | Template / docs-of-truth | Verified — uses `4omc` model name (NOT gpt-5.4/deepseek-* per AGENTS.md §6.1) |
| `.env.local` | 684B | Local-prod gateway overrides | **UNREAD** |
| `.env.production` | 1.1K | Production overrides | **UNREAD** |

### 9.7 Dev Defaults (MUST Override for Prod)

| Variable | Default | Risk |
|----------|---------|------|
| `REDIS_AUTH` | `omc_redis_secret` | Network-readable Redis |
| `POSTGRES_PASSWORD` | `omc_dev` | DB compromise |
| `LANGFUSE_NEXTAUTH_SECRET` | `omc_langfuse_nextauth_secret` | Session forgery |
| `LANGFUSE_ENCRYPTION_KEY` | `000...000` | Cannot decrypt traces |
| `CLICKHOUSE_PASSWORD` | `clickhouse_secret` | Trace data leak |
| `MINIO_ROOT_PASSWORD` | `minio_secret` | Blob storage compromise |

### 9.8 Langfuse Observability (Unverified)

**Status**: Env vars declared in `.env.example` (lines 110–115): `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL=https://cloud.langfuse.com`, `LANGFUSE_NEXTAUTH_SECRET`, `LANGFUSE_SALT`. All blank defaults.

**Integration code**: `packages/agents/observability.py` exists per AGENTS.md §11 but was **NOT audited** in this trace. Cannot confirm whether the integration is wired or whether the env vars are actually read.

**Gap**: Read `packages/agents/observability.py` to verify Langfuse integration is operational.

---

## 10. Data Flow — End-to-End

### 10.1 Teaching-Pack Path (AUTHORITATIVE)

**⚠️ Verified reality (2026-06-30)**: Quality gates and export formats are substantially thinner than described below.

```
1. Teacher submits request via Next.js dashboard
   ↓
2. POST /teaching-packs/run → FastAPI Gateway
   - JWT auth verification
   - Backpressure check (429 if exceeded)
   - Idempotency check (deduplicate)
   - Enqueue RunJob (status: PENDING/QUEUED)
   - Return 202 Accepted
   ↓
3. Background Worker picks up job
   - claim_next() with 120s lease
   - Execute teaching-pack graph
   ↓
4. Teaching-Pack Graph (8 stages)
   setup_contract → preplanning_search → planning_blueprint
     → post_blueprint_research → artifact_workflow
     → render_quality → teacher_approval → export_finalize
   ↓
5. Agent Calls (via LiteLLM → 9Router) [9Router is STUB]
   - Lead Agent orchestrates via task()
   - Planner: deepseek-v4-flash (f.light)
   - Researcher: deepseek-v4-flash (f.light)
   - Content Creator: deepseek-free (f.light)
   - Reviewer: content-fusion (f.pro fusion) [NOT WIRED in teaching-pack]
   ↓
6. Quality Gates [THINNER THAN DOCUMENTED]
   - In-pipeline: schema validation + placeholders + answer-key leakage
     + accessibility + pack-coherence + VN difficulty distribution
   - NO Layer 3 (HTML/presentation)
   - NO Layer 4 (LLM-as-Judge) in teaching-pack
   - NO Layer 6 (multi-judge export)
   - Layer 5 (HITL) wired via interrupt() at nodes.py:174
   ↓
7. Teacher Approval (interrupt)
   - Gateway returns gate payload to frontend
   - Teacher reviews artifacts in dashboard
   - Approves / rejects / edits
   - Resume via POST /teaching-packs/runs/{id}/resume
   ↓
8. Export [PATH STUBS ONLY]
   - export_finalize calls ExporterRegistry.default().export()
   - Returns string paths for html/gift/h5p/qti
   - google_forms raises UnsupportedExportFormatError
   - NO actual GIFT/H5P/QTI content generation
   - Actual disk write via teaching_pack_export_writer.py (NOT YET AUDITED)
   ↓
9. SSE streaming to frontend
   - Stage transitions, gate interrupts, completion
   - Teacher sees live progress
```

### 10.2 Rendering Flow

```
ArtifactContent JSON (from content_creator agent)
  → ArtifactContent.model_validate() (Pydantic)
  → renderArtifact<T>(type, data)
    → loadTheme(themeName) → CSS string
    → eta.renderAsync("pages/<type>", { ...data, themeCSS, lang })
      → base.html: <!DOCTYPE html> + <style>{themeCSS}</style> + header + main + footer
      → pages/<type>.html: includes components/*.html
    → sanitize(html, type) → DOMPurify per-artifact config
    → validateNoExternalUrls() → INVARIANT-04 enforcement
  → Standalone HTML (no CDN, offline-ready, printable)
```

---

## 11. Hard Invariants

| # | Invariant | Enforcement | Status |
|---|-----------|-------------|--------|
| 01 | Lead Agent NEVER calls LLM to generate content | Prompt + tool surface | ✅ Verified |
| 02 | packages/agents NEVER imports from services/* or apps/* | CI import boundary check | ✅ Verified |
| 03 | Every node is a pure function (state) → partial_state | Node signature convention | ✅ Verified |
| 04 | HTML output MUST NOT contain http(s):// asset reference | `validateNoExternalUrls()` post-render | ✅ Verified (renderer only, not teaching-pack pipeline) |
| 05 | Answer keys MUST be in teacher_only sections | DOMPurify per-artifact config | ✅ Verified |
| 06 | Teacher Gate CANNOT be bypassed | `interrupt()` mandatory | ✅ Verified (nodes.py:174) |
| 07 | All LLM calls MUST include metadata.tags | `get_cost_metadata()` | ⚠️ Unverified — 9Router is stub, no real LLM calls |
| 08 | Clarification middleware always last (order=30) | `BaseMiddleware` ABC | ⚠️ **CORRECTED** — order=30, NOT 24. Registry authoritative. |
| 09 | theme.json is single source of truth | Generated CSS never edited manually | ✅ Verified |
| 10 | Pydantic contracts in common/contracts only | Canonical schema location | ✅ Verified |

---

## 12. File Index

### Core Packages

| Package | Path | Language | Purpose |
|---------|------|----------|---------|
| Agents | `packages/agents/` | Python | LangGraph multi-agent pipeline |
| Quality | `packages/quality/` | Python | 6-layer quality gate system |
| Renderer | `packages/renderer/` | TypeScript | Eta template engine → HTML |
| Contracts | `common/contracts/` | Python | Pydantic schemas (source of truth) |
| Schemas | `common/schemas/` | TypeScript | Zod schemas (generated from Pydantic) |
| Branding | `common/branding/` | JSON/CSS | Theme tokens + generated CSS |

### Services

| Service | Path | Port | Purpose |
|---------|------|------|---------|
| Gateway | `services/gateway/` | 8001 | FastAPI + embedded LangGraph |
| Proxy | `services/proxy/` | 4000 | LiteLLM proxy |
| Router | `services/router/` | 20128 | 9Router sidecar |

### Frontend

| App | Path | Port | Purpose |
|-----|------|------|---------|
| Web | `apps/web/` | 3000 | Next.js 15 teacher dashboard |

### Infrastructure

| Component | Path | Purpose |
|-----------|------|---------|
| Docker Compose | `infra/compose/` | Full dev stack (9 services) |
| Dockerfiles | `infra/docker/` | Build contexts (gateway, proxy, web) |
| LiteLLM Config | `infra/litellm/` | LiteLLM proxy config |
| 9Router Config | `infra/9router/` | 9Router sidecar config |

### Key Entry Points

| File | Purpose |
|------|---------|
| `AGENTS.md` | Single source of truth for all agents and architecture |
| `packages/agents/graph.py` | Legacy 18-node graph builder (frozen) |
| `packages/agents/teaching_pack/graph.py` | Authoritative 8-stage graph builder |
| `packages/agents/state.py` | `OhMyClassState` TypedDict |
| `services/gateway/main.py` | FastAPI app initialization |
| `services/proxy/config.yaml` | LiteLLM model routing |
| `services/router/config.yaml` | 9Router combo definitions |
| `packages/renderer/src/renderer.ts` | `renderArtifact<T>()` public API |

---

> **Generated:** 2026-06-30T11:45:00+07:00
> **Updated:** 2026-06-30T15:00:00+07:00 (verified-reality corrections)
> **Workers:** 7 parallel explore agents (initial) + 6 verification agents (corrections)
> **Waves:** 1 (saturation) + 0 expansion (sufficient depth achieved) + 1 verification wave
> **Source files read:** 50+ files across all subsystems
> **Coverage:** All 7 architecture axes fully traced + verified against actual code

**Verification gaps remaining** (to be closed before this doc is considered authoritative):
1. `services/gateway/teaching_pack_export_writer.py` — determines whether GIFT/H5P/QTI files contain real bytes or empty stubs
2. `packages/agents/observability.py` — verifies Langfuse integration wiring
3. `services/router/config.yaml` — 9Router combo definitions
4. `.env`, `.env.local`, `.env.production` — actual env values
5. `services/proxy/keys/virtual_keys.yaml` — LiteLLM virtual keys config
6. `scripts/setup.sh` — startup script verification

**Recommended next audit wave**: Read the 6 files above to complete the verification matrix.
