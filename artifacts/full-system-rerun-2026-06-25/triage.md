# Full-System Rerun Triage - 2026-06-25

## Confirmed Cleanup

- `.claude/worktrees/` was deleted before the rerun.
- Docker cleanup completed successfully after the failed startup attempt.

## Failures

### Environment / Tooling

1. `lint-imports` is unavailable.
   - Evidence: `preflight-output.txt`, `lint-imports-output.txt`
   - Details: direct command missing; `uv run lint-imports` also fails to spawn `lint-imports`.
   - Impact: Python import boundary check cannot run.
   - Next action: install/configure the import-linter executable in the uv workspace, or update Makefile/scripts to use the correct command.

2. `.env` is missing.
   - Evidence: `docker-up-output.txt`
   - Details: compose reports `.env not found`.
   - Impact: stack startup is blocked.
   - Next action: create `.env` from `.env.example` with local-safe placeholders.

### Static / Type / Lint Failures

1. Ruff fails on first-party files after `.claude/worktrees/` cleanup.
   - Evidence: `ruff-output.txt`
   - First examples:
     - `common/branding/tests/test_generate_theme.py`: unused `os`, import order.
     - `common/contracts/__init__.py`: import order.
     - `common/contracts/answer_key.py`: `TC001` type-checking import.
     - `common/contracts/components/concept.py`: long lines.
   - Impact: Python lint gate is red.

2. basedpyright fails with many strict typing errors.
   - Evidence: `typecheck-python-output.txt`
   - Main patterns:
     - Missing type arguments for bare `dict`.
     - Unused imports.
     - Negative Pydantic validation tests passing invalid literals rejected by static types.
   - Impact: Python type gate is red.

3. TypeScript lint fails in `apps/web`.
   - Evidence: `lint-ts-output.txt`
   - Error: `next lint` is interpreted as invalid project directory `apps/web/lint`.
   - Impact: recursive TS lint fails before other packages can complete.
   - Next action: replace `next lint` with a compatible ESLint invocation for Next 16.

4. TypeScript dependency boundaries pass.
   - Evidence: `depcruise-output.txt`
   - Result: `no dependency violations found (316 modules, 311 dependencies cruised)`.

### Test / Build Failures

1. Pytest fails during collection.
   - Evidence: `pytest-output.txt`
   - Error: `ModuleNotFoundError: No module named 'tests.integration'` while collecting `tests/integration/test_full_pipeline.py`.
   - Impact: no Python test execution signal beyond collection.
   - Next action: fix test package discovery/import layout for `tests.integration`.

2. PNPM build fails before tests.
   - Evidence: `pnpm-build-output.txt`
   - Error: Turbo cannot resolve workspaces because root `package.json` is missing `packageManager`.
   - Impact: TS build and tests are blocked.
   - Next action: add root `packageManager`, likely `pnpm@10.6.0`.

3. Schema parity fails with real drift.
   - Evidence: `schema-parity-output.txt`
   - Drift:
     - `LessonPlan`: missing in Zod: `learning_objectives`, `learning_plan`, `methodology`; extra in Zod: `description`.
     - `ArtifactContent`: missing in Zod: `accessibility`, `sections`; extra in Zod: `artifacts`, `run_id`.
     - `JudgeOutput`: missing in Zod: `critical_issues`, `passed`, `rationale`; extra in Zod: `issues`, `score`.
   - Next action: run schema generation and review generated diffs.

### Docker / Runtime Failures

1. Docker build fails after daemon became reachable.
   - Evidence: `docker-build-output.txt`
   - Error: `lstat /Users/trung.ngo/Documents/zaob-dev/oh-my-class/infra/infra: no such file or directory`.
   - Impact: container build cannot complete.
   - Next action: inspect `infra/compose/docker-compose.yml` build contexts; likely paths are relative to the compose file and accidentally resolve as `infra/infra`.

2. Docker stack startup fails due to missing `.env`.
   - Evidence: `docker-up-output.txt`
   - Impact: no containers started; HTTP smoke cannot pass.

3. Runtime smoke fails because services are not running.
   - Evidence: `gateway-health.txt`, `frontend-health.txt`, `docker-ps.txt`
   - Result: HTTP `000`; compose `ps` shows no services.

## Recommended Fix Order

1. Add `packageManager` to root `package.json` to unblock Turbo build/tests.
2. Fix pytest collection for `tests.integration`.
3. Install or correct `lint-imports`/import-linter command.
4. Fix compose build contexts that resolve to `infra/infra`.
5. Create local `.env` from `.env.example` for stack smoke.
6. Run schema generation/parity review.
7. Address Ruff and basedpyright failures in batches.
8. Rerun full plan after these blocker fixes.
