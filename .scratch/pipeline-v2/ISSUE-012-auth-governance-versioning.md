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

Active-surface reconciliation: auth/governance verification should use active Teaching Pack route dependencies, ownership checks, stream-cookie auth restrictions, contract edit allowlists, and `/teaching-packs/*` preview/export/status surfaces. Historical `pipeline_v2_*` test names in the review are not implementation targets.

Evidence:
- Auth/ownership changes are in `services/gateway/auth/models.py`, `auth/dependencies.py`, `auth/jwt_handler.py`, and `auth/ownership.py`.
- Soft-delete and purge/retention are implemented in `services/gateway/soft_delete.py`, `purge.py`, and `retention.py` with migration `007_soft_delete_and_retention.py`.
- Identity hashing is implemented in `services/gateway/identity_hash.py`; schema version helpers are in `services/gateway/schema_version.py`.
- Tests cover owner/admin access edges, cross-tenant denial, soft-delete/purge/retention behavior, schema-version no-op migration, and identity hashing in `services/gateway/tests/test_pipeline_v2_auth.py`, `test_pipeline_v2_runs_router_auth_edges.py`, `test_soft_delete_retention.py`, `test_identity_hash.py`, and `test_run_creation_security.py`.
- Previous-version contract adapter coverage is now isolated in `services/gateway/tests/test_schema_version.py`: current `1.0` and previous `0.9` are supported, malformed/future versions are rejected, `0.9` draft fields migrate to the active `1.0` names without mutating input, and explicit current fields are preserved.
- Focused schema-version verification: `uv run pytest services/gateway/tests/test_schema_version.py -q` → `5 passed`; `uv run basedpyright services/gateway/schema_version.py services/gateway/tests/test_schema_version.py` → `0 errors`; `uv run python -m py_compile services/gateway/schema_version.py services/gateway/tests/test_schema_version.py` → success; manual driver verified `0.9 -> 1.0` adapter behavior and malformed/future version rejection.
- Generated/frontend API drift enforcement is now mechanical for the active Teaching Pack API: `apps/web/src/types/teaching-pack-api.ts` supplies the frontend contract used by `use-teaching-packs.ts`, while `scripts/verify_frontend_api_contracts.py` compares TypeScript status/gate unions and request/response interfaces against `RunStatus`, `TeachingPackGateName`, `TeachingPackGateAction`, and the active FastAPI route schemas in `services/gateway/routers/teaching_pack_schemas.py`.
- Focused frontend API drift verification: `uv run python scripts/verify_frontend_api_contracts.py` → contracts match; `uv run pytest services/gateway/tests/test_frontend_api_contracts.py -q` → `1 passed`; `uv run basedpyright scripts/verify_frontend_api_contracts.py services/gateway/tests/test_frontend_api_contracts.py` → `0 errors`; `pnpm --filter @oh-my-class/web typecheck` → passed; `pnpm --filter @oh-my-class/web test -- hooks.test.ts` → `95 passed`.
- Student-evidence shortest-TTL enforcement is now applied at the active Teaching Pack create seam. `services/gateway/retention.py` derives run retention from minimized `class_info`, and `services/gateway/run_creation.py` stores `retention_days=30` when `student_evidence` is present, so hard purge uses the student-evidence window instead of the 365-day run-metadata default.
- Focused retention verification: `uv run pytest services/gateway/tests/test_retention_policy.py services/gateway/tests/test_run_creation_security.py -q` → `4 passed`; `uv run basedpyright services/gateway/retention.py services/gateway/teaching_pack_store.py services/gateway/run_creation.py services/gateway/tests/test_retention_policy.py services/gateway/tests/test_run_creation_security.py` → `0 errors`; `uv run python -m py_compile services/gateway/retention.py services/gateway/teaching_pack_store.py services/gateway/run_creation.py services/gateway/tests/test_retention_policy.py services/gateway/tests/test_run_creation_security.py` → success.

Gaps:
- Previous-version schema adapter support is covered for the active `0.9 -> 1.0` draft transition, and generated/mechanically checked frontend API drift enforcement is covered for the active Teaching Pack API.
- Full OpenAPI code generation is still not introduced; the active Teaching Pack API now has a checked-in mechanical drift guard.
- Core tenant auth, ownership, retention, soft-delete, purge, and identity hashing primitives are implemented, but not every listed endpoint surface was independently proven in this review.
- Student-evidence minimization and shortest-TTL storage are now proven through the active create seam. Caveat: the broader legacy `services/gateway/tests/test_soft_delete_retention.py` still has an unrelated route-harness auth mismatch (`test_soft_deleted_run_hidden_from_status` returns 401 instead of its expected 404).
