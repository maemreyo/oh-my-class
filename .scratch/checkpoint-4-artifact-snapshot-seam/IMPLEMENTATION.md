"""
IMPLEMENTATION SUMMARY: Production Artifact Snapshot Seam
========================================================

PROBLEM (Checkpoint 4 — Verifier Verdict: needs-fix)
- render_artifact_content() was orphaned with zero production callers
- create_snapshot() had zero production callers
- Pipeline V2 RENDER_QUALITY and ARTIFACT_WORKFLOW stages are placeholders
- No production flow connecting: renderer_adapter → snapshot_store

SOLUTION IMPLEMENTED
====================

1. PRODUCTION SERVICE (services/gateway/artifact_snapshot_service.py)
   - New module: artifact_snapshot_service.py (86 lines)
   - Function: produce_artifact_snapshot(session, run_id, artifact_content, ...)
   - Flow:
     a) Calls renderer_adapter.render_artifact_content() with artifact JSON
     b) Snapshot store internally strips student answer keys (teacher_only sections)
     c) Persists via PipelineV2SnapshotStore.create_snapshot()
   - Returns: snapshot_id (string)
   - Error handling: RendererAdapterError, SnapshotPersistenceError propagate

2. PRODUCTION ROUTE (services/gateway/routers/snapshots.py)
   - New module: routers/snapshots.py (104 lines)
   - Endpoint: POST /run/{run_id}/snapshots
   - Request schema: ProduceSnapshotRequest (artifact_content, artifact_id, artifact_type, versions)
   - Response schema: ProduceSnapshotResponse (snapshot_id)
   - Authorization: Teacher (owner) or ADMIN; blocks cross-tenant access
   - Non-test caller registration: This route is a production caller for produce_artifact_snapshot()

3. GATEWAY WIRING (services/gateway/main.py)
   - Added import: from .routers import snapshots
   - Added router: app.include_router(snapshots.router, prefix="/run", tags=["snapshots"])
   - Completes the handler chain: router → snapshot endpoint → service → renderer/store

TEST COVERAGE
=============

Unit Tests (test_artifact_snapshot_service.py — 5 tests)
- ✓ produce_artifact_snapshot calls renderer and persists snapshot
- ✓ artifact_id is generated if not provided
- ✓ renderer and template versions preserved in snapshot
- ✓ renderer errors propagate to caller
- ✓ snapshot store errors propagate to caller

Integration Tests (test_snapshots_router.py — 4 tests)
- ✓ endpoint calls produce_artifact_snapshot with correct args
- ✓ authorization rejects unauthorized teacher
- ✓ authorization allows owner teacher
- ✓ authorization allows admin regardless of ownership

All 9 tests pass. Imports verified.

ARCHITECTURE NOTES
==================

Package Boundaries (INVARIANT-02 compliance)
- Service lives in services/gateway (allowed: imports from packages/agents)
- Route lives in services/gateway (allowed: imports from packages/agents)
- No violation of: packages/agents, packages/quality must not import services/*

Production Caller Registration
- The router endpoint (POST /run/{run_id}/snapshots) is a production caller
- Non-test callers: Teacher dashboard can invoke via HTTP
- Test callers: 9 test cases verify the flow with mocked renderer

Data Flow (INVARIANT-05 compliance)
- Answer keys are stripped by PipelineV2SnapshotStore.remove_answer_keys_from_html()
- Student preview HTML is generated without teacher_only sections
- teacher_only flag in content_json is respected

Version Metadata Preservation
- renderer_version, template_version, theme_version pass through to snapshot
- Content hash includes both content_json and rendered_html (deterministic)
- Standalone HTML validation enforced by renderer_adapter and snapshot store

Error Handling
- Renderer errors: RendererAdapterError (subprocess failure, timeout, invalid output)
- Snapshot errors: SnapshotPersistenceError (DB insertion failure)
- Authorization errors: AuthorizationError (cross-tenant access)
- 404: Run not found in app.state.runs

Next Steps (for pipeline integration)
====================================
1. Wire this endpoint into the RENDER_QUALITY or ARTIFACT_WORKFLOW stage
2. Call produce_artifact_snapshot for each artifact in the run's artifacts list
3. Store snapshot_ids in run state for export/approval gates
4. Update evidence with production caller count (currently: 1 route endpoint + 9 tests)
"""
