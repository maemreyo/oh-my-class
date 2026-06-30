# ADR-017: Topic Decomposition and Unit Fan-Out

## Status

**Decided** (2026-06-30) — A topic that needs more than one session is planned as a `LessonSequence` by a parent "unit" run, then fanned out into independent child session runs orchestrated at the application layer. Supersedes the implicit "1 run = 1 topic = 1 lesson" assumption for multi-session topics; single-lesson runs are unchanged.

## Context

`LessonPlan` is single-session hardwired (`topic: str`, `duration_minutes ≤ 180`, one Gagné cycle). `RunContract` is one run = one topic = one pack. The pipeline graph is linear with two HITL gates; there is no fan-out, no session cursor, no prerequisite graph (see `docs/reports/core/11-topic-decomposition-research.md`).

Teachers in the GDPT-2018 context routinely teach a **chủ đề** across multiple **tiết** (2–8). The system cannot represent this. We need multi-session decomposition that is pedagogically grounded (UbD → Gagné → Bloom + KC + CLT), production-ready, and integrates with the existing LangGraph runtime, quality gates, persona/methodology features, and teacher dashboard — without regressing the single-lesson flow and without patching half-measures.

## Decision

### Topology — two-tier (parent unit run + independent child session runs)

A unit is **not** a single long-lived execution. It is an application-level aggregate over LangGraph threads:

- **Parent run** (`mode="plan_unit"`, reuses the existing graph): `… → 02b_triage → unit_planner → gate_unit_approval → step_unit_prep → END`. It produces and freezes a `LessonSequence` + `UnitContext`, then ends.
- **Child runs** (`mode="generate_pack"`, the existing pipeline unchanged): one per session, linked by `parent_run_id` + `session_id`. Each is a real run — own `thread_id`, checkpointer, gates, healing, quality, export.
- **`unit_id == parent_run_id`** (no separate identity).

Rejected: in-graph fan-out via LangGraph `Send`/subgraphs — it rejoins children into one state/thread/checkpointer (Model A), defeating independent per-session resume/gate/observe.

### Intra-run vs inter-run boundary (LangGraph integration)

- **Intra-run** (parent or child) = pure LangGraph: one `thread_id = run_id`, `interrupt()` gates, `Command(resume=)`. Idiomatic, matches the existing pattern.
- **Inter-run** orchestration (fan-out, topological ordering, blocking) = application layer, where cross-run coordination already lives (`TeachingPackExecutor`). LangGraph has no native cross-thread orchestration by design; modelling long-lived waiting inside a node would pin an execution.

### UnitOrchestrator — stateless, fully-derived

The orchestrator holds **no** authoritative in-memory state. On each trigger (child event) it recomputes unit state from the DB (`lesson_sequence` + all children rows), then decides the next idempotent action. Core is a pure function `(sequence, children_states) → next_actions[]`. This makes it crash-safe (recompute on restart), horizontally scalable (no sticky state), and testable. The DB (children + sequence) is the single source of truth; unit status is **computed, never materialized**. An event-bus reactor drives it; a periodic reconciliation sweep provides at-least-once safety.

### Gating

- **One unit blueprint gate** (`UNIT_APPROVAL`): teacher reviews the whole sequence (session outlines, prereq DAG, durations, Bloom, per-session methodology, theme, `grounding_status`); `edit` = reorder/add/remove/edit before freeze. Children **skip `gate_01`** (their blueprint was approved as part of the sequence).
- **Content gate stays per-child** (`gate_02` `interrupt()` reused) but the UI **aggregates** all pending child gates of a unit into one dashboard with batch "Approve all".
- Sequence is **frozen** at approval; structural change = reject + replan.

### Lifecycle

Fail-isolated (a failed session never kills the unit); prerequisite **soft-block + teacher override**; session-level retry reuses run resume/healing; unit reaches `partially_complete` and is exportable before all sessions finish.

### Data model (thin sequence, child expands)

`unit_planner` produces a **coarse** sequence (per-session outline: objectives, ≤4 new KCs, recalled-KC refs, Bloom, duration, session-level prerequisites, primary methodology). Each child runs `planner_node(seed=SessionPlan)` in **expand mode** to fill the Gagné `learning_plan` + assessments, guarded against drift from the approved outline. Stable `session_id` is the domain key; `order_index` is display-only (reorder-safe before freeze).

Persistence extends the `runs` table (`parent_run_id`, `session_index`, `unit_role`, `lesson_sequence`, `shared_research`, persona snapshot) — nullable, backward-compatible. New contracts split domain (`lesson_sequence.py`, `class_profile.py`) from transport/view (`unit_view.py`); **all** go through the existing Pydantic → Zod codegen so BE/FE share types.

### Smart layers

- **Grounded planning:** `unit_planner` = retrieve grounding (GDPT-2018 / PPCT / age-band tables) → Curricular-CoT adapt → validate. Not pure-LLM.
- **Confidence + fail-closed:** emits `confidence` / `grounding_status` / `open_questions`; clarifies before planning when ungrounded + ambiguous; flags low-confidence choices on the gate.
- **Persona memory:** durable per-teacher `ClassProfile`, snapshotted into each `UnitContext`; drives duration, methodology, assume-vs-reteach, difficulty.
- **Decomposition memory:** teacher-approved (post-edit) sequences become template priors; per-teacher preference profile learned from edit diffs. Soft priors only.
- **Cross-unit `ClassKnowledgeGraph`** (networkx): longitudinal assume-vs-reteach + gap detection.
- **Cross-session coherence:** advisory lint (terminology, monotonic difficulty, prereq resolution) — never blocking.

### Quality (three tiers)

1. `SequenceConsistencyValidator` — deterministic HARD (acyclic DAG, Bloom ≥2, ≤4 KC/session, duration drift, prereq depth) in `unit_planner`.
2. Drift guard — deterministic HARD at child expand.
3. Cross-session coherence — advisory lint, lazy.

Per-session quality (existing Layers 1–4) is unchanged and remains the hard gate per pack.

## Consequences

- Single-lesson flow is unchanged (`unit_role="standalone"`); migration is additive nullable columns.
- Children reuse 100% of existing run infrastructure (gates, healing, quality, export, persistence, resume).
- Parallelism, retry, partial completion, and crash recovery come "for free" from independent runs + a stateless orchestrator.
- New surfaces are limited to genuinely new concerns (sequence editor, unit dashboard, orchestrator); transport/view types are codegen'd to prevent drift.
- A unit's liveness depends on the orchestrator + event bus, not a single graph execution — observability and the reconciliation sweep must cover it.

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
