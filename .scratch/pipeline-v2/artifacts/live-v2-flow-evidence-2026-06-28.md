# Pipeline V2 live flow evidence — 2026-06-28

## Scope

Validated the new Pipeline V2 surface documented in `.scratch/pipeline-v2/`, using the implemented `teaching_pack_*` modules and `/teaching-packs/*` API path.

## Documentation contract checked

Primary docs read:

- `.scratch/pipeline-v2/README.md`
- `.scratch/pipeline-v2/ISSUE-003-control-plane-executor.md`
- `.scratch/pipeline-v2/ISSUE-004-run-contract-setup-stage.md`
- `.scratch/pipeline-v2/ISSUE-007-artifact-workflow.md`
- `.scratch/pipeline-v2/ISSUE-008-rendered-preview-approval.md`
- `.scratch/pipeline-v2/ISSUE-009-quality-healing-safety.md`
- `.scratch/pipeline-v2/ISSUE-011-live-e2e-release-gates.md`

## Fixes applied before live test

- Added plural `/teaching-packs/runs` aliases to match the frontend hook path while preserving existing singular `/teaching-packs/run` routes.
- Added plural aliases for resume, status SSE, lifecycle, and snapshot preview routes.
- Started the Teaching Pack worker loop in gateway lifespan.
- Passed frozen contract payload from queued start jobs into worker initial graph state.
- Added active-gate listing to `TeachingPackControlStore`.
- Added status-change event emission for persisted status transitions.
- Fixed deterministic E2E schema detection so tests run instead of skip.
- Made V2 executor fail closed if the graph completes without export evidence, instead of silently marking the job completed while leaving the run pending.

## Verification commands

```bash
uv run pytest services/gateway/tests/test_teaching_pack_*.py \
  tests/e2e/test_teaching_pack_deterministic.py \
  tests/e2e/test_teaching_pack_scenarios.py -q
```

Result: `147 passed in 9.06s`.

```bash
uv run python -m py_compile \
  services/gateway/main.py \
  services/gateway/teaching_pack_executor.py \
  services/gateway/teaching_pack_worker.py \
  services/gateway/teaching_pack_control_store.py \
  services/gateway/teaching_pack_store.py \
  services/gateway/routers/teaching_pack_runs.py \
  services/gateway/routers/teaching_pack_stream.py \
  services/gateway/routers/teaching_pack_lifecycle.py \
  services/gateway/routers/teaching_pack_previews.py
```

Result: passed.

## Live HTTP evidence

Gateway launched with:

```bash
JWT_SECRET=dev-test-secret-minimum-32-characters \
LLM_BASE_URL=http://localhost:20228/v1 \
NINEROUTER_BASE_URL=http://localhost:20228/v1 \
uv run uvicorn services.gateway.main:app --host 0.0.0.0 --port 8001
```

Request:

```bash
POST /teaching-packs/runs
{
  "raw_request": "Dạy phân số tương đương cho lớp 5. Tạo lesson, worksheet, quiz.",
  "class_info": {
    "topic": "Phân số tương đương",
    "grade": 5,
    "subject": "math",
    "language": "vi",
    "student_count": 30
  }
}
```

Response:

```json
{
  "run_id": "f3ef16db-b85d-48c2-9d4e-4beb322e3628",
  "job_id": "job-a038fb9a-65c3-4559-8b59-eba3cc8df425",
  "status": "pending",
  "queued": false
}
```

Status replay:

```text
id: 1
event: teaching_pack.run.accepted
data: {"sequence":1,"job_id":"job-a038fb9a-65c3-4559-8b59-eba3cc8df425"}

id: 2
event: teaching_pack.status.changed
data: {"sequence":2,"status":"failed","stage":null,"reason":"missing_export_evidence"}

id: 3
event: teaching_pack.run.failed
data: {"sequence":3,"error":"V2 graph completed without export evidence"}
```

Database state:

```text
run failed
job completed 1
event 1 teaching_pack.run.accepted {...}
event 2 teaching_pack.status.changed {"status":"failed","stage":null,"reason":"missing_export_evidence"}
event 3 teaching_pack.run.failed {"error":"V2 graph completed without export evidence"}
```

## Current production-readiness verdict

V2 is not production-ready. The control-plane path is now observable and fail-closed, but the actual `packages/agents/teaching_pack` graph is still a placeholder skeleton. It completes without creating artifacts, rendered snapshots, content approval gates, approved snapshot ids, or HTML exports.

Remaining P0 blocker:

- Implement the real V2 graph stages behind `packages/agents/teaching_pack`: setup/contract, research, artifact workflow, rendered snapshot creation, content approval gate, export readiness, and final export evidence.

This blocker prevents completion of ISSUE-011 live 9Router matrix scenarios.