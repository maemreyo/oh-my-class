---
title: Pipeline V2 rendered preview snapshots and teacher approval
status: review-partial
labels: [pipeline-v2, renderer, approval, ui]
created: 2026-06-27
order: 8
blocked_by: [ISSUE-002-production-persistence, ISSUE-003-control-plane-executor, ISSUE-007-artifact-workflow]
adr_refs:
  - docs/adr/008-artifact-workflow-and-rendered-snapshots.md
  - docs/adr/005-generic-gate-resume-api.md
---

## Problem

Teachers should approve the actual rendered teaching pack, not raw JSON. V2 must render, validate, persist, and present standalone HTML snapshots before content approval.

## Scope

Implement rendered snapshot creation and approval flow.

Agent-ready tasks:

1. Integrate renderer as a V2 artifact pipeline stage before content approval.
2. Persist rendered snapshots through the Postgres artifact snapshot store.
3. Store content hash, HTML hash, renderer version, template version, theme version, standalone validity, and approval timestamps.
4. Add API endpoints for artifact metadata, student-safe preview, teacher preview with answer keys, and rendered snapshot retrieval.
5. Ensure preview payloads reference snapshots rather than embedding huge HTML in gate payloads.
6. Implement content approval gate payload with artifact preview refs and quality badges.
7. Ensure teacher approval records the exact approved snapshot ids.

## Out Of Scope

- Full frontend redesign beyond required approval components.
- Object storage adapter.
- Non-HTML export implementation.

## Acceptance Criteria

- Every generated core artifact can be rendered before Gate 2.
- Rendered HTML passes standalone no-external-asset validation before teacher approval.
- Student preview redacts teacher-only content and answer keys.
- Teacher preview can show answer keys with authorization.
- Gate 2 displays snapshot refs and quality status, not raw JSON dumps.
- Export uses approved snapshot ids.

## Test Plan

- Renderer integration tests for core artifact types.
- Snapshot persistence integration tests.
- API auth tests for student-safe vs teacher view.
- Presentation validation tests for no external assets and answer-key separation.
- Browser/manual QA for approval preview.

## Observability

- Emit events for render started/completed/failed, snapshot persisted, preview ready, and content approval required.
- Trace metadata includes artifact id, snapshot id, renderer version, and template version.

## Required Edge Cases And Tests

- Student preview never includes teacher-only sections, answer keys, correct-answer metadata, or hidden scrapeable answers.
- Teacher preview requires teacher/admin auth and can show answer keys intentionally.
- Rendered HTML rejects external `http(s)` assets, CDN links, external scripts, imports, and unmanaged JS runtimes.
- Snapshot hash changes when content/template/theme changes and remains stable for identical inputs.
- Approved snapshot id is the one exported; regenerating after approval creates a new snapshot requiring approval.
- Large HTML previews are retrieved by reference, not embedded in gate payloads.
- Renderer/template version mismatch is visible and blocks unsafe reuse.
- Preview endpoint denies cross-tenant access and soft-deleted runs.
- Browser/manual QA covers desktop, narrow viewport, print preview smoke, and iframe sandbox behavior.
- Tests cover render failure, invalid artifact JSON, missing snapshot, stale approval, and snapshot access after deletion.

## Rollback

If rendered approval is unstable, block V2 release rather than reverting to JSON approval. Rendered approval is required for production readiness.

## Ultrawork Review — 2026-06-27

Status: PARTIAL. Snapshot persistence and preview/approval APIs exist, but renderer integration and browser/manual QA are not fully proven.

Evidence:
- Snapshot data model and migration exist in `services/gateway/pipeline_v2_snapshot_models.py` and `services/gateway/alembic/versions/006_rendered_snapshot_metadata.py`.
- Snapshot storage and standalone validation are implemented in `services/gateway/pipeline_v2_snapshot_store.py`.
- Preview routes and schemas are implemented in `services/gateway/routers/pipeline_v2_previews.py` and `pipeline_v2_preview_schemas.py`.
- Tests cover metadata without huge HTML, student redaction, teacher preview answer keys, exact approved snapshot ids, non-standalone rejection, non-owner denial, hash stability, and external asset rejection in `services/gateway/tests/test_pipeline_v2_previews.py` and `test_pipeline_v2_snapshot_store.py`.

Gaps:
- I found API/snapshot evidence, not a full renderer-stage integration proof for every core artifact type.
- Browser/manual QA for approval preview, narrow viewport, print preview, and iframe sandbox was not found in staged evidence.
- Student preview rendering appears simplified in the gateway snapshot path rather than proven through the full Eta template renderer.
- Renderer/template version mismatch blocking, regenerated-after-approval snapshot invalidation, and preview endpoint cross-tenant checks were not fully proven by the reviewed tests.
