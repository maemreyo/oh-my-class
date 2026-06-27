---
title: Pipeline V2 tenant auth, data governance, retention, and contract versioning
status: review-partial
labels: [pipeline-v2, auth, governance, retention, versioning]
created: 2026-06-27
order: 12
blocked_by: [ISSUE-001-foundation-architecture, ISSUE-002-production-persistence, ISSUE-003-control-plane-executor]
adr_refs:
  - docs/adr/012-data-governance-and-versioning.md
  - docs/adr/004-production-run-persistence.md
---

## Problem

Pipeline V2 will persist teacher requests, optional student evidence, generated artifacts, rendered snapshots, events, and gate feedback. Production cannot rely on demo-user ownership, unversioned JSON blobs, or no deletion policy.

## Scope

Implement tenant-ready authorization, data governance, retention, deletion, contract versioning, and generated frontend API type checks.

Agent-ready tasks:

1. Add minimal tenant-ready model: `organization_id`, `teacher_id`, optional `class_id`, roles `teacher`, `school_admin`, `system_admin`.
2. Enforce ownership/role authorization in run, gate, artifact, preview, export, notification, and admin endpoints.
3. Add retention configuration by data class.
4. Implement soft-delete immediate access revocation and delayed hard purge job.
5. Ensure student evidence has shortest TTL and is minimized.
6. Add schema versions to every persisted V2 JSON contract and event payload.
7. Add read adapters for previous V2 versions.
8. Add generated or mechanically checked frontend API types from backend OpenAPI/contracts.
9. Ensure Langfuse receives hashed identity metadata only.

## Out Of Scope

- Full school/class management UI.
- Legal compliance workflow beyond product data lifecycle primitives.
- V1 data migration compatibility.

## Acceptance Criteria

- Non-owner teacher cannot read, resume, preview, export, cancel, or delete another teacher's run.
- School admin can access only runs within their organization.
- System admin can use safe recovery APIs.
- Soft-deleted runs are hidden and inaccessible immediately.
- Hard purge removes sensitive blobs/evidence according to retention policy.
- Versioned contracts can read current and one previous V2 schema version.
- Frontend generated/mechanically checked API types are part of CI.

## Required Edge Cases And Tests

- Cross-tenant run id guessing is rejected for every API.
- Teacher id in request body is ignored in favor of authenticated actor.
- Student-safe artifact endpoint redacts answer keys even for teacher-owned runs when requested as student view.
- Soft-deleted run denies artifact snapshot URL access.
- Purge job handles already-deleted rows, missing snapshots, and active runs safely.
- Retention config rejects negative TTLs and impossible combinations.
- Schema read adapter handles missing optional fields and rejects unsupported future versions.
- Generated frontend types detect drift when backend model changes.
- Langfuse metadata contains hashed ids and no raw email/name/class identifiers.

## Test Plan

- Real Postgres integration tests for ownership filters, retention, soft-delete, purge, and schema version adapters.
- API tests for teacher, school admin, system admin, and unauthorized user.
- Contract generation/check tests for frontend types.
- Privacy tests for identity hashing and student evidence minimization.

## Observability

- Persist compact events for delete requested, soft-deleted, purge completed, purge failed, schema adapter used, and authorization denial summary.
- Do not log raw student evidence or secrets.

## Rollback

Do not cut over V2 without this issue. Auth/governance gaps are production blockers.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Tenant auth, soft-delete, retention, schema versioning, and identity hashing exist, but generated frontend type drift and previous-version adapters are not fully proven.

Evidence:
- Auth/ownership changes are in `services/gateway/auth/models.py`, `auth/dependencies.py`, `auth/jwt_handler.py`, and `auth/ownership.py`.
- Soft-delete and purge/retention are implemented in `services/gateway/soft_delete.py`, `purge.py`, and `retention.py` with migration `007_soft_delete_and_retention.py`.
- Identity hashing is implemented in `services/gateway/identity_hash.py`; schema version helpers are in `services/gateway/schema_version.py`.
- Tests cover owner/admin access edges, cross-tenant denial, soft-delete/purge/retention behavior, schema-version no-op migration, and identity hashing in `services/gateway/tests/test_pipeline_v2_auth.py`, `test_pipeline_v2_runs_router_auth_edges.py`, `test_soft_delete_retention.py`, `test_identity_hash.py`, and `test_run_creation_security.py`.

Gaps:
- `schema_version.py` currently supports only `1.0`; I did not find a real previous-version adapter beyond no-op current-version migration.
- Generated/mechanically checked frontend OpenAPI type drift enforcement was not found as staged evidence.
- Core tenant auth, ownership, retention, soft-delete, purge, and identity hashing primitives are implemented, but not every listed endpoint surface was independently proven in this review.
- Student evidence has a retention class and minimization helpers, but shortest-TTL enforcement through the full pipeline was not proven end-to-end.
