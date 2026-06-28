# Teaching Pack Rearchitecture Plan

## Purpose

The Teaching Pack architecture replaces the current V1 pipeline with a production-ready, stage-based architecture. The goal is not to patch the current Researcher/Content Creator failure modes, but to rebuild the run harness around durable persistence, smart contracts, search/research grounding, artifact-level generation, rendered preview approval, operational hardening, governance, and live 9Router production validation.

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

- [ADR-002: Teaching Pack Stage Architecture](../adr/002-teaching-pack-stage-architecture.md)
- [ADR-003: RunContract and Conditional Human-in-the-Loop](../adr/003-run-contract-and-conditional-hitl.md)
- [ADR-004: Production Run Persistence](../adr/004-production-run-persistence.md)
- [ADR-005: Generic Gate Resume API](../adr/005-generic-gate-resume-api.md)
- [ADR-006: Research Engine](../adr/006-research-engine.md)
- [ADR-007: Adaptive LLM Transport](../adr/007-adaptive-llm-transport.md)
- [ADR-008: Artifact Workflow and Rendered Snapshots](../adr/008-artifact-workflow-and-rendered-snapshots.md)
- [ADR-009: Quality, Healing, and Safety Gates](../adr/009-quality-healing-and-safety-gates.md)
- [ADR-010: Teaching Pack Testing and Observability](../adr/010-teaching-pack-testing-and-observability.md)
- [ADR-011: Operational Hardening](../adr/011-operational-hardening.md)
- [ADR-012: Data Governance, Authorization, and Versioning](../adr/012-data-governance-and-versioning.md)
- [ADR-013: Prompt, Template, and Rubric Governance](../adr/013-prompt-template-rubric-governance.md)

## Issue Index

Implementation issues are retained in the historical scratch archive and are not renamed as part of the runtime/product cutover. The active Teaching Pack architecture tracks these work areas:

| Order | Area | Purpose |
|---:|---|---|
| 1 | Foundation architecture | Teaching Pack skeleton, module boundaries, contracts, config shape |
| 2 | Production persistence | Postgres run store, event log, snapshots, checkpointer |
| 3 | Control-plane executor | Background executor, resume API, gate registry, status machine |
| 4 | Run contract setup stage | Smart preflight, Quickstart, RunContract, conditional gates |
| 5 | Research engine | Search/fetch/rank/extract/synthesize Research Engine |
| 6 | Adaptive LLM transport | Per-task streaming policy, 9Router transport, Langfuse metadata |
| 7 | Artifact workflow | Artifact-level generation, workflow state, bounded parallelism |
| 8 | Rendered preview approval | Rendered snapshots, preview APIs, approval gate payloads |
| 9 | Quality, healing, and safety | Per-artifact gates, typed healing, safety gates, export readiness |
| 10 | UI/UX cutover | Frontend Teaching Pack run flow, gate shell, artifact progress, preview UX |
| 11 | Live E2E release gates | Real Postgres and live 9Router release validation |
| 12 | Auth, governance, and versioning | Tenant auth, retention, deletion, schema/API versioning |
| 13 | Operations hardening | Idempotency, jobs/leases, cancellation, recovery, budgets |
| 14 | Notifications and admin recovery | In-app notifications and safe admin recovery actions |
| 15 | Prompt, template, and rubric governance | Prompt/template/theme/rubric registries and evals |

## Core Decisions Locked By Grilling

- Teaching Pack replaces V1; do not preserve V1 internals.
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
- Tenant-ready authorization, retention, deletion, and schema versioning are required in Teaching Pack.
- Idempotency, job leases, cancellation, stuck recovery, budgets, and backpressure are production requirements.
- Prompts, templates, themes, and rubrics are versioned production modules with evals and hash validation.
- Live 9Router E2E is required for production-readiness evidence.

## Deferred From Initial Teaching Pack

- Non-core artifacts: drill, infographic, and future catalog types.
- Non-HTML exports: GIFT, H5P, QTI, Google Forms.
- Full school/class management UI.
- External notification channels such as email/Zalo/Telegram.
- Object storage adapter for rendered snapshots.
- Full dynamic LangGraph fan-out for artifacts.
- Prompt editing admin UI and full A/B prompt experimentation platform.

## Production Readiness Definition

Teaching Pack is production-ready only when:

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
