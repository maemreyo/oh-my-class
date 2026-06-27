# Pipeline V2 Rearchitecture Plan

## Purpose

Pipeline V2 replaces the current V1 pipeline with a production-ready, stage-based architecture. The goal is not to patch the current Researcher/Content Creator failure modes, but to rebuild the run harness around durable persistence, smart contracts, search/research grounding, artifact-level generation, rendered preview approval, operational hardening, governance, and live 9Router production validation.

## Target User Journey

1. Teacher creates a teaching-pack request.
2. The system clarifies or confirms only when needed.
3. The system optionally confirms a search plan when search direction, cost, or sensitivity matters.
4. The system creates a lesson blueprint and asks the teacher to approve or edit it.
5. The system researches, generates, validates, heals, renders, and stores artifacts individually.
6. Teacher reviews rendered HTML previews, not raw JSON.
7. The system exports approved standalone HTML snapshots.
8. Teachers and admins receive in-app notifications for required action, completion, failure, and escalation.

## Architecture Decisions

- [ADR-002: Pipeline V2 Stage Architecture](../adr/002-pipeline-v2-stage-architecture.md)
- [ADR-003: RunContract and Conditional Human-in-the-Loop](../adr/003-run-contract-and-conditional-hitl.md)
- [ADR-004: Production Run Persistence](../adr/004-production-run-persistence.md)
- [ADR-005: Generic Gate Resume API](../adr/005-generic-gate-resume-api.md)
- [ADR-006: Research Engine](../adr/006-research-engine.md)
- [ADR-007: Adaptive LLM Transport](../adr/007-adaptive-llm-transport.md)
- [ADR-008: Artifact Workflow and Rendered Snapshots](../adr/008-artifact-workflow-and-rendered-snapshots.md)
- [ADR-009: Quality, Healing, and Safety Gates](../adr/009-quality-healing-and-safety-gates.md)
- [ADR-010: Pipeline V2 Testing and Observability](../adr/010-pipeline-v2-testing-and-observability.md)
- [ADR-011: Operational Hardening](../adr/011-operational-hardening.md)
- [ADR-012: Data Governance, Authorization, and Versioning](../adr/012-data-governance-and-versioning.md)
- [ADR-013: Prompt, Template, and Rubric Governance](../adr/013-prompt-template-rubric-governance.md)

## Issue Index

All implementation issues live in one folder: `.scratch/pipeline-v2/`.

| Order | Issue | Purpose |
|---:|---|---|
| 1 | `.scratch/pipeline-v2/ISSUE-001-foundation-architecture.md` | V2 skeleton, module boundaries, contracts, config shape |
| 2 | `.scratch/pipeline-v2/ISSUE-002-production-persistence.md` | Postgres run store, event log, snapshots, checkpointer |
| 3 | `.scratch/pipeline-v2/ISSUE-003-control-plane-executor.md` | Background executor, resume API, gate registry, status machine |
| 4 | `.scratch/pipeline-v2/ISSUE-004-run-contract-setup-stage.md` | Smart preflight, Quickstart, RunContract, conditional gates |
| 5 | `.scratch/pipeline-v2/ISSUE-005-research-engine.md` | Search/fetch/rank/extract/synthesize Research Engine |
| 6 | `.scratch/pipeline-v2/ISSUE-006-adaptive-llm-transport.md` | Per-task streaming policy, 9Router transport, Langfuse metadata |
| 7 | `.scratch/pipeline-v2/ISSUE-007-artifact-workflow.md` | Artifact-level generation, workflow state, bounded parallelism |
| 8 | `.scratch/pipeline-v2/ISSUE-008-rendered-preview-approval.md` | Rendered snapshots, preview APIs, approval gate payloads |
| 9 | `.scratch/pipeline-v2/ISSUE-009-quality-healing-safety.md` | Per-artifact gates, typed healing, safety gates, export readiness |
| 10 | `.scratch/pipeline-v2/ISSUE-010-ui-ux-cutover.md` | Frontend V2 run flow, gate shell, artifact progress, preview UX |
| 11 | `.scratch/pipeline-v2/ISSUE-011-live-e2e-release-gates.md` | Real Postgres and live 9Router release validation |
| 12 | `.scratch/pipeline-v2/ISSUE-012-auth-governance-versioning.md` | Tenant auth, retention, deletion, schema/API versioning |
| 13 | `.scratch/pipeline-v2/ISSUE-013-operations-hardening.md` | Idempotency, jobs/leases, cancellation, recovery, budgets |
| 14 | `.scratch/pipeline-v2/ISSUE-014-notifications-admin-recovery.md` | In-app notifications and safe admin recovery actions |
| 15 | `.scratch/pipeline-v2/ISSUE-015-prompt-template-rubric-governance.md` | Prompt/template/theme/rubric registries and evals |

## Core Decisions Locked By Grilling

- V2 replaces V1; do not preserve V1 internals.
- User-facing journey remains stable, but backend/frontend contracts may break and be migrated together.
- RunContract is resolved early and revised append-only.
- HITL is conditional and risk-based.
- Search is a first-class module, biased toward running before planning, with optional search-plan confirmation.
- Content generation is artifact-level, not pack-level.
- Teacher content approval is rendered HTML preview approval.
- Postgres is the production source of truth for run state, events, contracts, gates, workflow, jobs, notifications, and snapshots.
- Langfuse is observability only, not persistence.
- Adaptive streaming is per task; streaming alone is not the JSON reliability solution.
- Quality/healing/safety are per-artifact first, pack-level second.
- Tenant-ready authorization, retention, deletion, and schema versioning are required in V2.
- Idempotency, job leases, cancellation, stuck recovery, budgets, and backpressure are production requirements.
- Prompts, templates, themes, and rubrics are versioned production modules with evals and hash validation.
- Live 9Router E2E is required for production-readiness evidence.

## Deferred From Initial V2

- Non-core artifacts: drill, infographic, and future catalog types.
- Non-HTML exports: GIFT, H5P, QTI, Google Forms.
- Full school/class management UI.
- External notification channels such as email/Zalo/Telegram.
- Object storage adapter for rendered snapshots.
- Full dynamic LangGraph fan-out for artifacts.
- Prompt editing admin UI and full A/B prompt experimentation platform.

## Production Readiness Definition

Pipeline V2 is production-ready only when:

- all ADR-linked issues are implemented or consciously deferred with a replacement decision;
- every issue's `Required Edge Cases And Tests` section is satisfied or has explicit follow-up issues;
- real Postgres integration tests pass;
- deterministic E2E regression suite passes;
- live 9Router release matrix passes with documented run ids and artifacts;
- rendered HTML exports are standalone and contain no external assets;
- student-facing previews contain no teacher-only answer keys;
- tenant authorization prevents cross-run access;
- duplicate run/resume/cancel requests are idempotent;
- worker lease expiry and recovery are tested;
- cancellation, timeout, escalation, retention, and soft-delete behavior are tested;
- prompt/template/rubric version/hash validation passes;
- generated frontend API types match backend contracts;
- Langfuse can be unavailable without stopping runs;
- create/resume HTTP requests return quickly and do not perform long-running graph work inline.
