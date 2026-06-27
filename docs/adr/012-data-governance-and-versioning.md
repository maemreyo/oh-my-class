# ADR-012: Data Governance, Authorization, and Versioning

## Status

**Decided** (2026-06-27) — Pipeline V2 is tenant-ready, privacy-conscious, retention-aware, and uses versioned persisted contracts with generated frontend API types.

## Context

Pipeline V2 persists run metadata, teacher requests, optional student evidence, search metadata, generated artifacts, rendered snapshots, gate feedback, events, and trace metadata. It also exposes teacher/admin APIs and frontend views. Production readiness requires clear ownership, retention, deletion, contract evolution, and frontend/backend type alignment.

## Decision

Authorization model:

- Add tenant-ready ownership from the start.
- Persist `organization_id`, `teacher_id`, and optional `class_id` on runs and related records where needed.
- Roles: `teacher`, `school_admin`, `system_admin`.
- All APIs authorize by persisted run ownership and role, not request body values.
- Artifact endpoints enforce student-safe vs teacher/admin views.
- Langfuse receives hashed identity metadata only.

Retention and deletion:

- Retention is configurable by data class.
- Student evidence has the shortest TTL and is minimized by default.
- Raw fetched pages are not persisted by default; compact source metadata/snippets may be retained with TTL.
- Delete requests soft-delete immediately, revoke access immediately, and schedule delayed hard purge.
- A minimal tombstone/audit record may remain.

Contract versioning:

- Every persisted JSON contract has `schema_version`.
- Write path writes current versions only.
- Read path supports current and known previous V2 versions through read adapters.
- Breaking changes require version bump, migration or read adapter, fixture updates, and compatibility tests.
- V1 compatibility is not required.

API types:

- V2 frontend types are generated or mechanically checked from backend contracts/OpenAPI.
- Frontend must not depend on raw LangGraph state shapes.
- Event payloads are versioned.
- Long-term production UI must not use loose `Record<string, unknown>` as primary API contract.

Prompt/policy/template/rubric version metadata:

- Registry metadata and hashes are persisted where relevant so old runs can be explained.
- Startup/test validation should detect version/hash drift.

## Consequences

- The app is not locked into a single-demo-teacher model.
- Old V2 runs remain readable through normal schema evolution.
- Teacher and student data have explicit lifecycle controls.
- Frontend/backend drift is caught mechanically.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Teacher-only ownership | Simpler | Hard to add schools/classes later without data migration pain |
| Immediate hard delete | Simple semantics | Risky during active jobs and harder to audit |
| No read adapters | Less code | Old runs break after schema changes |
| Manual frontend types | Fast initially | Easy to drift from API contracts |
