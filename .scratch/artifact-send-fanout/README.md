# Artifact Send Fan-Out Epic

ADR: `docs/adr/020-langgraph-send-artifact-fanout.md`

Goal: migrate single-run artifact generation from an imperative batch call to a LangGraph-native, wave-based `Send` pipeline with deterministic reducer fan-in, per-artifact workflow status, scoped-regeneration parity, concurrency caps, teacher-facing partial-status UX, and rollbackable rollout.

## Issues

1. `001-state-and-reducer-foundation.md` — generation cycle ids and reducer-backed workflow states.
2. `002-generate-one-artifact-node.md` — standalone LangGraph worker node for one artifact.
3. `003-wave-router-and-fanin.md` — wave-based Send router and materializer behind feature flag.
4. `004-scoped-regeneration-parity.md` — route healing and teacher scoped rejection through the Send pipeline.
5. `005-concurrency-and-budget-wiring.md` — domain cap plus top-level RunnableConfig `max_concurrency`.
6. `006-teacher-facing-partial-status.md` — gate/API/frontend status UX for partial generation.
7. `007-rollout-and-e2e-evidence.md` — rollout flag, real graph E2E, release evidence.
8. `008-cleanup-old-imperative-path.md` — retire alternate merge/orchestration scaffolding after rollout.

## Dependency order

`001` → `002` → `003` → `004` → `005` → `006` → `007` → `008`

This epic supersedes the narrow `.scratch/agent-interaction/004b-parallel-fanout-send.md` placeholder for artifact generation. The older issue remains useful as historical context for reducer prerequisites and reviewer/content-creator sub-agent decomposition, but ADR-020 is now the decision of record for artifact fan-out in the teaching-pack runtime.
