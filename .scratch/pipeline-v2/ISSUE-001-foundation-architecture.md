---
title: Pipeline V2 foundation architecture and stage graph skeleton
status: ready-for-agent
labels: [pipeline-v2, architecture, foundation]
created: 2026-06-27
order: 1
blocked_by: []
adr_refs:
  - docs/adr/002-pipeline-v2-stage-architecture.md
  - docs/adr/003-run-contract-and-conditional-hitl.md
  - docs/adr/010-pipeline-v2-testing-and-observability.md
---

## Problem

The current pipeline is a mostly linear V1 graph with fragile pack-level assumptions. Pipeline V2 needs a clean stage-based foundation before implementing persistence, gates, research, generation, and UI cutover.

## Scope

Create the V2 architectural skeleton without preserving V1 internals.

Agent-ready tasks:

1. Define V2 package/module boundaries for stage graph, contracts, config, executor ports, persistence ports, gates, research engine, artifact workflow, and quality/healing.
2. Add V2 stage graph skeleton with stages: `setup_contract`, `preplanning_search`, `planning_blueprint`, `post_blueprint_research`, `artifact_workflow`, `render_quality`, `teacher_approval`, `export_finalize`.
3. Add explicit interfaces/ports for run store, artifact snapshot store, event writer, executor, LLM transport, search/fetch clients, and renderer.
4. Add config loading shape: code defaults, YAML policy, `.env` deployment overrides, request overrides, RunContract snapshot.
5. Update docs to point to Pipeline V2 as the target architecture.

## Out Of Scope

- Implementing Postgres schema.
- Implementing real Research Engine behavior.
- Implementing frontend UI.
- Running live 9Router E2E.

## Acceptance Criteria

- V2 modules do not import from `services/*` or `apps/*` from inside `packages/*`.
- Stage graph skeleton compiles with placeholder stage implementations.
- Interfaces are small, typed, and independently testable.
- Config loader validates policy YAML and deployment env shape.
- Existing import boundary checks still pass.

## Test Plan

- Unit tests for config loading and stage graph construction.
- Import boundary checks.
- Smoke test that V2 graph can be instantiated without invoking LLMs.

## Observability

- Define canonical stage names and event names.
- Define trace metadata keys but do not require full Langfuse implementation in this issue.

## Required Edge Cases And Tests

- Stage graph construction fails fast when required config or policy files are invalid.
- Stage names are stable and cannot collide with legacy V1 node names in events/traces.
- Package boundaries are enforced for every new V2 module.
- Placeholder stages cannot silently call LLMs or external services.
- V2 contracts include schema/version fields where they will be persisted.
- Config loader handles missing env vars, invalid YAML, invalid enum values, negative caps, and impossible budgets.
- Test that importing V2 modules has no side effects such as DB connections, network calls, or Langfuse initialization.
- Test that the stage graph can be instantiated repeatedly without shared mutable state leakage.
- Test that V2 stage metadata is serializable for event/log usage.

## Rollback

Revert V2 skeleton files and docs references. This issue should not modify production V1 routes yet.
