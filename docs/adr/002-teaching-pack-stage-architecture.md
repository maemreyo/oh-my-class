# ADR-002: Teaching Pack Stage Architecture

## Status

**Decided** (2026-06-27) — Replace the current linear V1 pipeline with a production-ready Teaching Pack stage architecture.

## Context

The current pipeline reaches the first teacher gate, but live full-flow runs fail after approval because Researcher and Content Creator are long-running, pack-level, and fragile. The current graph also mixes setup, research, generation, validation, rendering, approval, and export concerns in one mostly linear flow.

Teaching Pack must prioritize production readiness over patching V1. The teacher-facing journey remains stable: create a request, clarify or confirm when needed, approve the blueprint, watch artifact progress, review rendered previews, and export.

## Decision

Build Teaching Pack as the replacement architecture. Do not preserve V1 internals or exact legacy step numbering.

Teaching Pack uses stage boundaries:

1. `setup_contract` — diagnostic mode decision, smart preflight, RunContract resolution, conditional contract/clarification gate.
2. `preplanning_search` — lightweight search need classification, search plan, optional search-plan HITL, pre-planning search brief.
3. `planning_blueprint` — Planner creates the lesson blueprint; teacher approves or edits it.
4. `post_blueprint_research` — Research Engine creates compact shared and artifact-specific research guidance.
5. `artifact_workflow` — artifact-level generation with bounded parallelism, per-artifact workflow state, validation, and healing.
6. `render_quality` — render standalone HTML snapshots, validate presentation, and run adaptive quality review.
7. `teacher_approval` — teacher reviews rendered previews, not raw JSON.
8. `export_finalize` — export approved snapshots and finalize the run.

A modular top-level graph should call stage nodes or stage subgraphs. Artifact generation starts as an `ArtifactOrchestrator` deep module rather than immediate dynamic LangGraph fan-out.

## Consequences

- The official architecture moves from exact 13-step internals to stage-based Teaching Pack.
- UI can still show friendly progress stages rather than low-level node names.
- Existing V1 code may be used as reference but is not a compatibility constraint.
- Teaching Pack requires new contracts, persistence, executor, gates, research engine, artifact workflow, and UI components.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Patch V1 directly | Smaller diff | Preserves fragile pack-level assumptions and synchronous HTTP execution |
| Teaching Pack in parallel with long-lived feature flag | Easier rollback | More compatibility work; user chose not to preserve V1 |
| Stage-based Teaching Pack replacement | Clean production architecture | Larger migration and stronger test requirements |
