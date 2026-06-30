# ADR-017: Topic Decomposition and Unit Fan-Out

## Status

**Decided** (2026-06-30) — A topic that needs more than one session is planned as a `LessonSequence` by a parent "unit" run, then fanned out into independent child session runs orchestrated at the application layer. Supersedes the implicit "1 run = 1 topic = 1 lesson" assumption for multi-session topics; single-lesson runs are unchanged.

## Context

`LessonPlan` is single-session hardwired (`topic: str`, `duration_minutes ≤ 180`, one Gagné cycle). `RunContract` is one run = one topic = one pack. The pipeline graph is linear with two HITL gates; there is no fan-out, no session cursor, no prerequisite graph (see `docs/reports/core/11-topic-decomposition-research.md`).

Teachers in the GDPT-2018 context routinely teach a **chủ đề** across multiple **tiết** (2–8). The system cannot represent this. We need multi-session decomposition that is pedagogically grounded (UbD → Gagné → Bloom + KC + CLT), production-ready, and integrates with the existing LangGraph runtime, quality gates, persona/methodology features, and teacher dashboard — without regressing the single-lesson flow and without patching half-measures.

## Decision

### Topology — two-tier (parent unit run + independent child session runs)

A unit is **not** a single long-lived execution. It is an application-level aggregate over LangGraph threads.

**Authoritative runtime = the teaching-pack stage runtime** (`packages/agents/teaching_pack/graph.py` `build_teaching_pack_graph`, driven by `TeachingPackExecutor` + `TeachingPackWorker` + `TeachingPackJobStore` + the run sweeper). The older step-based `packages/agents/graph.py` (`build_oh_my_class_graph`) is **legacy** and is not extended by this feature.

- **Parent run** (`mode="plan_unit"`): a mode-aware stage branch after `SETUP_CONTRACT` — `TRIAGE → UNIT_PLANNING → unit_approval gate → UNIT_PREP → END`. It produces and freezes a `LessonSequence` + `UnitContext`, then ends. It does **not** run `artifact_workflow`/`render_quality`/`teacher_approval`/`export_finalize`.
- **Child runs** (`mode="generate_pack"`, the existing stage sequence unchanged): one per session, linked by `parent_run_id` + `session_id`. Each is a real run — own `thread_id`, checkpointer, gates, healing, quality, export. Children are enqueued through the existing `TeachingPackExecutor`/`TeachingPackJobStore`/`TeachingPackWorker`.
- **`unit_id == parent_run_id`** (no separate identity).
- Gates are stage-boundary interrupts registered in `teaching_pack_gate_registry` and driven via `POST /teaching-packs/runs/{id}/resume` (the same path as `contract_confirmation`/`blueprint_approval`/`content_approval`); the legacy `/run/approvals` route is frozen and fail-closed against unknown gates.

Rejected: in-graph fan-out via LangGraph `Send`/subgraphs — it rejoins children into one state/thread/checkpointer (Model A), defeating independent per-session resume/gate/observe.

### Intra-run vs inter-run boundary (LangGraph integration)

- **Intra-run** (parent or child) = pure LangGraph: one `thread_id = run_id`, `interrupt()` gates, `Command(resume=)`. Idiomatic, matches the existing pattern.
- **Inter-run** orchestration (fan-out, topological ordering, blocking) = application layer, where cross-run coordination already lives (`TeachingPackExecutor`). LangGraph has no native cross-thread orchestration by design; modelling long-lived waiting inside a node would pin an execution.

### UnitOrchestrator — stateless, fully-derived

The orchestrator holds **no** authoritative in-memory state. On each trigger it recomputes unit state from durable storage (`TeachingPackJobStore` + run rows: parent `lesson_sequence` + children `RunStatus`), then decides the next idempotent action. Core is a pure function `decide(sequence, children_states) → next_actions[]` that returns the full set of ready sessions; a `unit_fanout_concurrency` cap controls how many spawn at once (Phase 1 = 1 / sequential; Phase 2 raises it — no code fork). This makes it crash-safe (recompute on restart), horizontally scalable (no sticky state), and testable.

**Correctness depends only on the durable substrate, never on the in-memory event bus.** The reactor is a hook invoked by `TeachingPackCompletionRecorder`/worker when a child settles (completed/failed/gate-pending); `packages/agents/events.py` (in-memory) is used **only** for SSE/observability deltas. The reconciliation sweep extends the existing run sweeper to recompute `generating`/`in_review` units from the DB (at-least-once backstop). Child spawning is guarded by a DB unique constraint `(parent_run_id, session_id)` plus the app-level key `fanout:{unit_id}:{seq_revision}`; a failed session is retried by resuming its existing child run, not by creating a new row. Unit/session lifecycle states (`blocked`, `partially_complete`, `complete`, per-session display states) are **computed in `UnitView`, never persisted** — `RunStatus` is unchanged.

### Gating

- **One unit blueprint gate** (`UNIT_APPROVAL`): teacher reviews the whole sequence (session outlines, prereq DAG, durations, Bloom, per-session methodology, theme, `grounding_status`); `edit` = reorder/add/remove/edit before freeze. Children **skip `blueprint_approval` (gate_01)** (their blueprint was approved as part of the sequence).
- **Content gate stays per-child** (`content_approval` (gate_02) `interrupt()` reused) but the UI **aggregates** all pending child gates of a unit into one dashboard with batch "Approve all".
- Sequence is **frozen** at approval; structural change = reject + replan.

### Lifecycle

Fail-isolated (a failed session never kills the unit); prerequisite **soft-block + teacher override**; session-level retry reuses run resume/healing; unit reaches `partially_complete` and is exportable before all sessions finish.

### Data model (thin sequence, child expands)

`unit_planner` produces a **coarse** sequence (per-session outline: objectives, ≤4 new KCs, recalled-KC refs, Bloom, duration, session-level prerequisites, primary methodology). Each child runs `planner_node(seed=SessionPlan)` in **expand mode** to fill the Gagné `learning_plan` + assessments, guarded against drift from the approved outline. Stable `session_id` is the domain key; `order_index` is display-only (reorder-safe before freeze).

Persistence extends the `runs` table (`parent_run_id`, `session_index`, `unit_role`, `lesson_sequence`, `shared_research`, persona snapshot) — nullable, backward-compatible. New contracts split domain (`lesson_sequence.py`, `class_profile.py`) from transport/view (`unit_view.py`); **all** go through the existing Pydantic → Zod codegen so BE/FE share types.

### Sub-agents (new + enhanced)

- **New `unit_planner`** — coarse multi-session decomposition (distinct task from single-lesson `planner`).
- **New `sequence_critic`** — an independent adversarial reviewer invoked inside `UNIT_PLANNING` (`unit_planner → sequence_critic → bounded self-repair → validator`). The deterministic validator catches *structural* errors (DAG/CLT/Bloom); the critic catches *semantic pedagogy* errors a single pass misses (wrong prerequisite order, a split that fragments one concept, a missing core sub-concept, redundant re-teaching). Remaining critiques surface on the unit gate.
- **New `coherence_judge`** — unit-scoped, post-generation, advisory (issue 016).
- **Enhanced `planner`** — `seed`/expand mode + drift guard. **Enhanced `researcher`** — unit-shared vs session-augment scope. **Enhanced `content_creator`** — consumes per-session `methodology_primary`.
- All are LangGraph nodes in the stage runtime; LLM via the existing transport; prompts via `PromptCompiler` + registry; repair reuses the existing recovery pattern. No new agent framework. Curricular-CoT stays *inside* `unit_planner` (staged prompting), not split into separate agents.

### Smart layers

- **Grounded planning:** `unit_planner` = retrieve grounding (GDPT-2018 / PPCT / age-band tables) → Curricular-CoT adapt → critic → validate. Not pure-LLM. Curriculum norms (session counts, Bloom distribution) are **grounded operational defaults from PPCT/sample plans, not universal law**.
- **Confidence + fail-closed:** emits `confidence` / `grounding_status` / `open_questions`; clarifies before planning when ungrounded + ambiguous; flags low-confidence choices on the gate.
- **Persona memory:** durable per-teacher `ClassProfile`, snapshotted into each `UnitContext`; drives duration, methodology, assume-vs-reteach, difficulty.
- **Decomposition memory:** teacher-approved (post-edit) sequences become template priors; per-teacher preference profile learned from edit diffs. Soft priors only.
- **Cross-unit `ClassKnowledgeGraph`** (networkx): longitudinal assume-vs-reteach + gap detection.
- **Cross-session coherence:** advisory lint (terminology, monotonic difficulty, prereq resolution) — never blocking.

### Quality (three tiers)

1. `SequenceConsistencyValidator` — deterministic HARD: acyclic DAG; ≤4 **new** KCs/session (`recalled_kc_ids` are references, never counted); Bloom rule (≥2 levels **and** an apply-or-higher level unless the topic is pure-recall); duration drift; prereq depth. Session count is an **advisory** check against the grounded norm, not a hard gate.
2. Drift guard — deterministic HARD at child expand.
3. Cross-session coherence (`coherence_judge`) — advisory lint, lazy.

Per-session quality (existing Layers 1–4) is unchanged and remains the hard gate per pack. `sequence_critic` adds an adversarial pedagogy pass before the gate.

## Consequences

- Single-lesson flow is unchanged (`unit_role="standalone"`); migration is additive nullable columns.
- Children reuse 100% of existing run infrastructure (gates, healing, quality, export, persistence, resume).
- Parallelism, retry, partial completion, and crash recovery come "for free" from independent runs + a stateless orchestrator.
- New surfaces are limited to genuinely new concerns (sequence editor, unit dashboard, orchestrator); transport/view types are codegen'd to prevent drift.
- A unit's liveness depends on the orchestrator + durable job/run store (not a single graph execution, not the in-memory event bus) — the reconciliation sweep is the correctness backstop.
- Targets the teaching-pack stage runtime; the legacy `build_oh_my_class_graph` and `/run/approvals` are frozen, not extended.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| In-state fan-out (Model A: session cursor in one run) | Minimal contract surface | Breaks "1 run = 1 pack"; every gate/node must know "current session"; 1 failure dirties the whole run; no independent approve/retry; hard to parallelize |
| LangGraph `Send`/subgraph fan-out | Native map-reduce | Rejoins to one state/thread/checkpointer = Model A; cannot gate one session independently |
| Separate `UnitPlannerGraph` + executor | Strong SoC | Duplicates preflight/quickstart/executor/checkpointer/events |
| Decomposition as inert metadata (teacher re-runs manually) | Trivial | No automation; prerequisite DAG/quality become decoration |
| Fat `SessionPlan` (N full LessonPlans up front) | Teacher approves exact output | Mega-prompt degrades quality (report §4.2); unreviewable gate; no per-session parallel planning |
| Orchestrator with in-memory state | Simple to write | Not crash-safe, not scalable, second source of truth to desync |
| Materialized unit status on parent | Fast reads | Classic sync bug (child changes, parent stale) |
