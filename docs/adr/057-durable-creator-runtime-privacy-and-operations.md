# ADR-057: Durable Creator Runtime, Privacy, and Operations

## Status

**Accepted** (2026-07-10) — Persist every meaningful domain boundary, keep LangGraph state thin, scale with Postgres-backed workers, and enforce tiered privacy, observability, and administrative authority.

## Context

A full-breadth run can contain planning, strategy, research, twelve artifact workflows, variants, approvals, versions, exports, and live-session publication. Carrying all objects in LangGraph checkpoint state would create large, replay-sensitive blobs. Keeping only final artifacts would make crash recovery repeat LLM work and weaken reproducibility.

The current gateway already has Postgres-backed run jobs, leases, heartbeats, a sweeper, Redis support, and checkpointers. The simplest production path is to deepen those boundaries and separate workers rather than add a new broker.

Durability also increases privacy obligations. Teacher sources, student evidence, raw fetched data, prompts, traces, artifacts, and exports do not share one retention need.

## Decision

### Persist every durable domain boundary

The runtime persists versioned references for:

- Teaching Brief drafts and Run Contract revisions;
- lesson blueprint and component strategy revisions;
- Research Briefs, Source Collections, and source-conflict decisions;
- Content Briefs;
- artifact generation cycles and workflow states;
- `ArtifactDocument`, `AnswerSet`, Language Version, Content Variant, and asset versions;
- quality reports, scorecards, healing history, and authority decisions;
- gates, responses, anchored review notes, and approvals;
- rendered snapshots and manifests;
- export records and manifests;
- budget ledgers and operational recovery events.

Completed durable outputs are reused after restart. Idempotent resume does not repeat an LLM call merely because a gateway or worker process restarted. Approved versions re-export reproducibly.

### Thin LangGraph state

Teaching-pack graph state carries typed IDs, active revisions, stage and branch summaries, generation-cycle IDs, and routing decisions. Durable domain payloads live in package-owned stores accessed through explicit ports. Reducers merge branch references and workflow summaries, not giant content blobs.

The stage graph remains the orchestration authority. Package modules do not import gateway implementation code. The gateway composes store and transport adapters.

### Postgres lease queue with separate workers

V1 keeps the durable Postgres-backed job queue and runs teaching-pack workers as processes separate from the HTTP gateway. Workers claim jobs with leases, heartbeat, bounded attempts, eligibility time, idempotency, and per-run concurrency and budget limits. The sweeper reclaims stale work and escalates timed-out gates.

Redis remains an optional hot path for pub/sub and circuit-breaker coordination; it is not the durable job authority. No Celery, Kafka, RabbitMQ, or other broker is added without measured throughput evidence.

### Progressive result SLO

The primary latency metric is time to first reviewable artifact, not time until every possible artifact and export is complete. Standard-mode targets are stage- and family-specific, with an initial goal of contract/plan resolution within roughly 30 seconds when no gate is required and a first reviewable lesson within roughly two minutes. Remaining artifacts stream progressively and may complete asynchronously.

Only quality-gated reviewable versions are presented as trustworthy output. Unvalidated drafts are not displayed as final content.

### Multi-dimensional resource budgets

Every run and artifact has governed budgets for latency, tokens, calls, retries, healing attempts, and concurrency. Logical model routes resolve through a versioned capability-routing policy. Snapshots record logical route, actual provider/model, prompt, schema, and routing-policy versions.

Fallback is permitted only within an approved compatible model set. Free providers are not treated as unlimited. Paid or unapproved emergency providers are not used.

### Operational-only administration

System administrators may release stale leases, retry idempotent work, use an already-approved compatible route, restore checkpoint execution, or mark terminal failure. They may not edit teaching intent, strategy, or content; relax safety or quality; approve artifacts; or hide provenance. Recovery events are audited and teacher-visible when they change run state or timing.

### Tiered retention and deletion

Authored content, versions, and their compact provenance remain until teacher or organization deletion policy applies. Raw fetched pages, full prompts and outputs, debug ledgers, and student evidence use short TTLs, minimization, and redaction. Snapshots and exports follow the content lifecycle. Non-content audit hashes may have a longer legal retention.

Deletion has a 30-day soft-delete recovery window, followed by asynchronous hard erasure or tombstoning across runs, versions, source documents, media references, snapshots, exports, and sensitive traces. Shared assets are erased only when unreferenced or explicitly selected. A legal hold may block hard deletion and must be visible.

### Resource scopes and tenant isolation

Teaching Recipes, Source Collections, Media Assets, and Class Profiles use explicit scopes:

- `private_teacher` by default;
- `organization` after an explicit publish action and privacy/license validation;
- `system` for code-governed resources.

Generation lookup and caches never cross tenant scope. Normalized fingerprints include tenant and resource scope and exclude raw teacher text, student names, emails, and individual student evidence.

### Bounded preference learning

Typed feedback events may update bounded, decayed teacher or organization preference multipliers. They never override hard policy, objective coverage, pedagogy evidence, renderability, or safety. V1 does not fine-tune models, mutate reviewed pedagogy knowledge, or store raw edits as hidden memory.

### Privacy-preserving observability

Production observability captures structured metadata and hashes by default: IDs, versions, route/model metadata, token/call/latency, error classes, quality scores, policy decisions, and output hashes. Full prompt/output capture is dev/test opt-in or a time-limited, redacted, audited diagnostic mode.

Teacher Decision Provenance comes from persisted domain decisions, not raw Langfuse traces.

## Consequences

- Runs survive crash and deployment without repeating completed model work.
- Graph checkpoints remain compact and replay-safe.
- Worker capacity scales horizontally without introducing another distributed system.
- Reproducibility and privacy coexist through tiered data rather than “store everything” or “recompute everything.”
- Administrative recovery cannot become an invisible content override.

## Considered Options

- **Full payloads in graph state**: rejected because checkpoint size and replay ambiguity grow with every capability.
- **Recompute planning/research after restart**: rejected because it changes provenance and repeats costly work.
- **In-process gateway workers**: rejected for Full-Breadth V1 because HTTP scaling and generation capacity should be independent.
- **External broker in V1**: rejected because the durable Postgres lease model already owns the required semantics.
- **Full production prompt/output capture**: rejected because it expands PII and content exposure.
- **Soft delete forever**: rejected because it fails the intended privacy lifecycle.

## References

- ADR-004 Production Run Persistence
- ADR-007 Adaptive LLM Transport
- ADR-010 Teaching Pack Testing and Observability
- ADR-011 Operational Hardening
- ADR-012 Data Governance and Versioning
- ADR-027 Circuit Breaker Scope
- ADR-034 Scale and Operations Platform
