# ADR-020: LangGraph Send Artifact Fan-Out

## Status

**Decided** (2026-07-01) — Artifact generation inside a single teaching-pack run will move from an imperative batch call to a LangGraph-native, wave-based `Send` fan-out. The migration is phased behind a rollout flag. The current runtime remains unchanged until the graph path has deterministic reducers, per-artifact workflow states, scoped-regeneration parity, concurrency caps, and teacher-facing partial-status UX.

## Context

The authoritative teaching-pack runtime is a LangGraph `StateGraph`, but artifact generation is still an imperative call inside the `artifact_workflow` stage: `_artifact_workflow(...)` builds a batch `ContentCreatorNodeState`, calls `content_creator_node(...)`, then writes the full `artifacts` list back to state. `content_creator_node(...)` already loops over artifact types and makes one LLM call per type, so the natural parallel boundary exists but is hidden inside one node function.

A research pass and grilling session found three important as-built facts:

1. LangGraph `Send(node_name, payload)` can only target a graph node registered by name; there is no `generate_one_artifact` node today.
2. `TeachingPackState.artifact_chunks` already has an order-stable reducer (`stable_merge_artifacts`) but is scaffold-only: no node reads or writes it.
3. `services/gateway/artifact_workflow.py::ArtifactOrchestrator` already models dependency waves and per-artifact failure isolation, but it is not wired into the production graph path.

The system also has a teacher-facing quality and approval flow. A partial artifact failure must not degrade into a vague whole-run crash when enough structured status exists to explain which artifact failed, which was skipped, and what action the teacher or system can take next.

## Decision

### 1. Use a real LangGraph worker node as the `Send` target

Add `generate_one_artifact` as a registered graph node. It generates exactly one artifact type and writes only to reducer-backed branch channels. `artifact_workflow` remains the coordinator/router for generation cycles; it does not become the worker.

The worker receives a minimal payload: `run_id`, `artifact_generation_id`, `artifact_type`, `lesson_plan`, `research_brief`, `theme`, `revision_feedback`, and dependency artifacts from prior waves. It does not receive the entire `TeachingPackState`.

### 2. Keep `artifacts` canonical; use `artifact_chunks` as generation-cycle staging

`artifact_chunks` is the reducer-backed staging channel for branch results. `artifacts` remains the canonical downstream state consumed by `render_quality`, teacher approval, export, and API surfaces.

Every generation cycle has an `artifact_generation_id` (or revision) recorded on chunks and workflow states. Fan-in materializes only chunks from the current generation cycle, so checkpoint replay and old reducer values cannot pollute a new cycle.

### 3. Add reducer-backed per-artifact workflow status

Add `artifact_workflow_states` as a reducer-backed channel keyed by `artifact_id` or `workflow_id`, sorted deterministically. Every `generate_one_artifact` branch writes one workflow state, even on failure or skip.

Expected artifact-level failures become workflow states (`failed`, `skipped`, `escalated`) instead of throwing. Infrastructure failures, programmer errors, cancellation, and corrupted graph/checkpointer state still throw so LangGraph can fail fast or retry at runtime level.

### 4. Use dependency waves, not all-at-once fan-out

Artifact generation is wave-based:

- Wave 0: `lesson`
- Wave 1: `worksheet`, `quiz`, `drill`
- Wave 2: `recap`

The dependency DAG and wave scheduling should be extracted from the existing `ArtifactOrchestrator` design into package-level planning utilities. The graph issues `Send` for one wave, fan-in materializes results and statuses, then conditionally loops to the next wave if required dependencies passed.

### 5. Keep quality authority in `render_quality`

`generate_one_artifact` performs only generation-local validation: schema, artifact type match, parse/shape checks, and safe error summarization. `render_quality` remains the pack-level quality authority for coherence, answer leakage, pedagogical alignment, FACT, HTML/presentation, and export readiness.

### 6. Route all generation and regeneration through the same pipeline

Initial generation, quality healing, and teacher scoped rejection all create a new generation cycle and use the same wave-based `Send` pipeline. The old imperative `_merge_regenerated_artifacts` path is retired or reduced to a pure helper inside the fan-in materializer.

Scoped regeneration preserves accepted artifacts, drops rejected artifact types, and merges only current-generation chunks. Current code is type-scoped once an artifact of that type is rejected; the UI and gate payload must make that behavior explicit.

### 7. Cap concurrency at domain and runtime layers

Use two layers:

- Domain layer: the wave router only issues sends for the current wave and respects the configured artifact parallelism.
- Runtime layer: graph invocation passes top-level `RunnableConfig.max_concurrency`, alongside `configurable.thread_id`.

The budget ledger does not enforce parallelism; it records and guards resource usage. The existing `teaching_pack_thread_config` type must be widened to represent the real `RunnableConfig` shape.

### 8. Teacher UX becomes per-artifact, not binary run failure

Teacher-facing gate payloads and dashboard views should expose per-artifact status: passed, regenerating, failed, skipped due dependency, or escalated. Export remains fail-closed: no export if required artifacts are missing or failed. Errors are summarized safely and actionably, never as raw provider stack traces.

### 9. Migration is phased and rollbackable

Do not ship this as a big bang. The implementation lands in slices: state/reducers, standalone worker, graph fan-out behind a feature flag, scoped-regeneration parity, concurrency/budget wiring, teacher UX, rollout evidence, then cleanup.

## Consequences

- Artifact generation becomes more scalable and observable without abandoning the authoritative LangGraph runtime.
- Per-artifact statuses make partial failure understandable to teachers and support safer automated retries.
- Reducer-backed state and generation ids keep fan-in deterministic under parallel completion, checkpoint replay, and scoped regeneration.
- The graph gains more nodes and conditional loops, so tests must cover topology, failure, concurrency, and UI payloads before runtime cutover.
- `ArtifactOrchestrator` becomes a source of reusable planning concepts, not a second production orchestration path.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Keep imperative batch generation | Lowest implementation risk | Serial LLM calls, weak per-artifact observability, harder scoped retry |
| Point `Send` at `artifact_workflow` | Minimal new node names | Router and worker responsibilities collapse; high risk of loops and accidental concurrent writes |
| Fan out all artifact types at once | Maximum parallelism | Violates lesson/quiz/recap dependency semantics and weakens coherence |
| Use `ArtifactOrchestrator` inside one node | Reuses existing limiter/waves | Not LangGraph-native; hides branch state from checkpointer/streaming; duplicates orchestration model |
| Make `artifacts` itself reducer-backed | Fewer fields | Blurs canonical downstream state with branch staging; harder scoped-regeneration reasoning |
| Throw on every artifact failure | Simple runtime semantics | Bad teacher UX; one malformed artifact hides successful siblings |
