# Full-System Test Execution Plan - 2026-06-25

## Scope

This plan validates the current `oh-my-class` repository across local tests, static checks, schema parity, Docker buildability, and runtime smoke surfaces.

Known gaps are treated as findings, not hidden coverage:

- `tests/e2e/` is empty.
- `tests/integration/test_full_pipeline.py` is a placeholder.
- `common/schemas` has a test script but no test files.
- `packages/quality/tests/test_layer6_export.py` is placeholder coverage.
- Several quality modules are stubs: FACT, pedagogical checks, age checks, responsive checks, export multi-judge, calibration.
- Several LangGraph pipeline nodes are pass-through dummies: preflight, quickstart, blueprint, pack scope, visual engine, research, finalize. The graph `llm_judge` node returns `8.0`.

## Scenario Contract

### Scenario 1: Unit Test Health

Pass condition: Python pytest and TypeScript tests exit 0.

Evidence:

- `artifacts/full-system-2026-06-25/pytest-output.txt`
- `artifacts/full-system-2026-06-25/pnpm-test-output.txt`

### Scenario 2: Static Integrity

Pass condition: lint, typecheck, and import boundary commands exit 0.

Evidence:

- `artifacts/full-system-2026-06-25/ruff-output.txt`
- `artifacts/full-system-2026-06-25/lint-imports-output.txt`
- `artifacts/full-system-2026-06-25/typecheck-python-output.txt`
- `artifacts/full-system-2026-06-25/lint-ts-output.txt`
- `artifacts/full-system-2026-06-25/depcruise-output.txt`

### Scenario 3: Contract Sync

Pass condition: Pydantic to Zod schema parity check exits 0.

Evidence:

- `artifacts/full-system-2026-06-25/schema-parity-output.txt`

### Scenario 4: Container Buildability

Pass condition: Docker compose build exits 0.

Evidence:

- `artifacts/full-system-2026-06-25/docker-build-output.txt`

### Scenario 5: Runtime Smoke

Pass condition: Docker stack starts, containers are healthy/running, gateway and frontend respond over HTTP.

Evidence:

- `artifacts/full-system-2026-06-25/docker-up-output.txt`
- `artifacts/full-system-2026-06-25/docker-ps.txt`
- `artifacts/full-system-2026-06-25/gateway-health.txt`
- `artifacts/full-system-2026-06-25/frontend-health.txt`
- `artifacts/full-system-2026-06-25/gateway-docs.html`

## Execution Waves

### Wave 0: Preflight

Create the artifact directory and capture tool versions:

```bash
mkdir -p artifacts/full-system-2026-06-25
python3 --version
node --version
pnpm --version
uv --version
docker --version
ruff --version
basedpyright --version
lint-imports --version
```

### Wave 1: Static Checks

```bash
ruff check .
lint-imports
bash scripts/typecheck.sh
pnpm -r lint
pnpm depcruise --validate .dependency-cruiser.cjs .
```

### Wave 2: Unit Tests

```bash
uv run pytest packages/agents packages/quality common/contracts services/gateway tests/ -v --tb=short
pnpm build
pnpm -r test
```

### Wave 3: Schema Parity

```bash
python scripts/verify_schema_parity.py
```

### Wave 4: Docker Build

```bash
docker compose -f infra/compose/docker-compose.yml build
```

### Wave 5: Runtime Smoke

```bash
docker compose -f infra/compose/docker-compose.yml up -d
docker compose -f infra/compose/docker-compose.yml ps
curl -s http://localhost:8001/health
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
curl -s http://localhost:8001/docs
```

### Wave 6: Triage And Cleanup

Create:

- `artifacts/full-system-2026-06-25/summary.md`
- `artifacts/full-system-2026-06-25/triage.md`

Cleanup command:

```bash
docker compose -f infra/compose/docker-compose.yml down -v
```

## Failure Triage

Failures are classified as:

- Environment issue: missing tool, Docker unavailable, port conflict, missing env.
- Known gap: placeholder test, empty E2E surface, explicit stub.
- Execution-blocking code failure: real test/static check failure in current code.
- Flaky: failure passes on isolated retry.

No production code is changed during this run.
