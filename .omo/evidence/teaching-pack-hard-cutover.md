# Teaching Pack Hard Cutover Evidence

Date: 2026-06-28

## Scope

Hard-cut runtime/product naming from `pipeline-v2` / `pipeline_v2` / `PipelineV2` to Teaching Pack naming with no compatibility aliases.

Canonical surfaces verified:

- External route prefix: `/teaching-packs`
- Run creation route: `/teaching-packs/run`
- Old route `/pipeline-v2/run`: not registered, returns 404
- Event namespace: `teaching_pack.*`
- Python package/module naming: `teaching_pack_*`, `TeachingPack*`
- Frontend naming: `TeachingPack*`, `teaching-packs-*`, query key `teaching-pack`
- Runtime evidence filename: `teaching-pack-run-evidence-{run_id}.md`

Historical Alembic revision filenames under `services/gateway/alembic/versions/002-004` intentionally retain old revision identifiers/history. Historical `.omo` and `.scratch` evidence/plan archives were intentionally not rewritten.

## Local Database Repair for Verification

The local Postgres schema was drifted before final verification:

- `alembic_version` was `008_notifications`
- later 010/011 objects already existed (`run_budget_ledgers`, `run_jobs.eligible_at`)
- `release_evidence` / `provider_evidence` were missing

Repair applied only to the local verification DB:

```bash
uv run alembic -c alembic.ini upgrade 009_release_evidence
uv run alembic -c alembic.ini stamp 011_queued_job_eligible_at
uv run alembic -c alembic.ini upgrade head
uv run alembic -c alembic.ini current
```

Result: `012_provider_evidence_column (head)`.

The 012 migration test then passed:

```bash
uv run pytest services/gateway/tests/test_migration_012_provider_evidence.py -q
# 4 passed in 0.48s
```

## Search Gates

Runtime/product old-name search, excluding historical Alembic revision files and non-runtime agent docs:

```bash
rg -n "pipeline-v2|pipeline_v2|PipelineV2|teaching_packs\." services packages apps tests common docs \
  --glob '!**/node_modules/**' \
  --glob '!**/.venv/**' \
  --glob '!services/gateway/alembic/versions/**' \
  --glob '!docs/agents/**'
```

Result: no output.

Filename search:

```bash
rg --files services packages apps tests common docs | rg "pipeline-v2|pipeline_v2|PipelineV2"
```

Result: only historical Alembic revision filenames remain:

- `services/gateway/alembic/versions/002_pipeline_v2_persistence.py`
- `services/gateway/alembic/versions/003_pipeline_v2_control_tables.py`
- `services/gateway/alembic/versions/004_pipeline_v2_run_jobs.py`

## API Surface Smoke

Manual TestClient smoke:

```python
old_response = client.post('/pipeline-v2/run', json={...})
new_response = client.post('/teaching-packs/run', json={...})
```

Observed result:

```python
{'old_status': 404, 'new_status': 202, 'new_keys': ['job_id', 'queued', 'run_id', 'status']}
```

The disposable smoke run for teacher `manual-smoke-teacher` was deleted afterward.

## Verification Commands

Backend gateway tests:

```bash
uv run pytest services/gateway/tests -q
# 602 passed, 12 skipped in 18.98s
```

Agent Teaching Pack tests:

```bash
uv run pytest packages/agents/tests/teaching_pack packages/llm_client/tests -q
# 36 passed in 1.94s
```

Frontend tests:

```bash
pnpm --filter @oh-my-class/web test
# 7 test files passed, 95 tests passed
```

Frontend typecheck:

```bash
pnpm --filter @oh-my-class/web exec tsc --noEmit
# passed, no output
```

Frontend build:

```bash
pnpm --filter @oh-my-class/web build
# Finished TypeScript in 3.4s
```

Package-boundary audit:

```bash
uv run lint-imports
# packages-no-import-services KEPT
# common-is-the-floor KEPT
# layered-architecture KEPT
# Contracts: 3 kept, 0 broken.
```

Touched gateway test lint/warning cleanup:

```bash
uv run ruff check services/gateway/tests/test_approvals_router.py \
  services/gateway/tests/test_artifacts_router.py \
  services/gateway/tests/test_error_handler.py \
  services/gateway/tests/test_notifications_router_admin.py \
  services/gateway/tests/test_run_contract_routes.py \
  services/gateway/tests/test_runs_router.py \
  services/gateway/tests/test_snapshots_router.py \
  services/gateway/tests/test_soft_delete_retention.py \
  services/gateway/tests/test_teaching_pack_auth.py \
  services/gateway/tests/test_teaching_pack_idempotency_security.py \
  services/gateway/tests/test_teaching_pack_previews.py \
  services/gateway/tests/test_teaching_pack_runs_router.py \
  services/gateway/tests/test_teaching_pack_runs_router_auth_edges.py \
  services/gateway/tests/test_teaching_pack_runs_router_edges.py \
  services/gateway/tests/test_webhooks_error.py
# All checks passed!
```

## Warning Cleanup

- Added `"type": "module"` to `apps/web/package.json` to remove Node module-type warning.
- Fixed `apps/web/src/hooks/use-error-logger.test.ts` logger mock shape.
- Switched gateway tests from `fastapi.testclient.TestClient` to `starlette.testclient.TestClient`.
- Added `httpx2` to `services.gateway` dependencies so Starlette's TestClient no longer emits the `install httpx2` deprecation warning.
- Moved gateway-coupled integration tests from `packages/agents/tests` to `services/gateway/tests` so package-boundary checks stay clean.
- Decoupled `packages.llm_client.config` from `packages.agents.config.models`; `packages.llm_client` now owns its env-backed LLM client settings.
- Reran backend and frontend tests/builds with no warning summary output.

## Plan Status

`.omo/plans/teaching-pack-hard-cutover.md` checklist is complete.
