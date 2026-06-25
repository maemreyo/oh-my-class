# Full-System Rerun Summary - 2026-06-25

Plan file: `docs/plans/full-system-test-plan-2026-06-25.md`

Requested cleanup completed: `.claude/worktrees/` was deleted before this rerun.

## Overall Result

The rerun is still not green. Removing `.claude/worktrees/` reduced the scan scope, and Docker is now reachable, but multiple repo/tooling gates remain red.

| Wave    | Surface                          |                       Result | Evidence                                                                             |
| ------- | -------------------------------- | ---------------------------: | ------------------------------------------------------------------------------------ |
| 0       | Preflight                        |                         FAIL | `preflight-output.txt`                                                               |
| 1a      | Ruff                             |                         FAIL | `ruff-output.txt`                                                                    |
| 1b      | Python import boundaries         |      FAIL / tool unavailable | `lint-imports-output.txt`                                                            |
| 1c      | Python typecheck                 |                         FAIL | `typecheck-python-output.txt`                                                        |
| 1d      | TypeScript lint                  |                         FAIL | `lint-ts-output.txt`                                                                 |
| 1e      | TypeScript dependency boundaries |                         PASS | `depcruise-output.txt`                                                               |
| 2a      | Python tests                     |           FAIL at collection | `pytest-output.txt`                                                                  |
| 2b      | TypeScript build/tests           | FAIL at build; tests skipped | `pnpm-build-output.txt`                                                              |
| 3       | Schema parity                    |  FAIL with real parity drift | `schema-parity-output.txt`                                                           |
| 4       | Docker build                     | FAIL with compose path error | `docker-build-output.txt`                                                            |
| 5       | Runtime smoke                    |   FAIL / stack did not start | `docker-up-output.txt`, `docker-ps.txt`, `gateway-health.txt`, `frontend-health.txt` |
| Cleanup | Docker down                      |                         PASS | `docker-down-output.txt`                                                             |

## Changes Versus First Run

- `.claude/worktrees/` is gone, so Ruff now reports first-party files instead of agent worktree copies.
- Docker daemon is reachable; build no longer fails on missing Docker socket.
- Docker build now fails on compose path resolution: `lstat .../infra/infra: no such file or directory`.
- Schema parity now ran via `uv run python` and reports real Pydantic/Zod drift instead of shell `python` missing.
- Docker cleanup succeeds.

## Key Evidence

- Preflight: `lint-imports` still unavailable directly and via `uv run lint-imports`.
- Ruff: first failures are unused import/import ordering/type-checking import issues in `common/branding/tests/test_generate_theme.py`, `common/contracts/__init__.py`, and `common/contracts/answer_key.py`; total log remains large.
- basedpyright: strict typing errors remain, especially missing generic type arguments and negative validation tests that intentionally pass invalid literals.
- TS lint: `next lint` in `apps/web` still fails with `Invalid project directory provided ... apps/web/lint`.
- Pytest: collected 934 items but failed during collection on `tests/integration/test_full_pipeline.py` with `ModuleNotFoundError: No module named 'tests.integration'`.
- PNPM build: Turbo still fails because root `package.json` lacks `packageManager`.
- Schema parity drift:
  - `LessonPlan`: Pydantic has `learning_objectives`, `learning_plan`, `methodology`; Zod has extra `description`.
  - `ArtifactContent`: Pydantic has `accessibility`, `sections`; Zod has extra `artifacts`, `run_id`.
  - `JudgeOutput`: Pydantic has `critical_issues`, `passed`, `rationale`; Zod has extra `issues`, `score`.
- Docker build: compose warns `version` is obsolete, then fails resolving `/infra/infra`.
- Docker up: blocked by missing `.env`.
- Runtime smoke: gateway and frontend return HTTP `000`; no containers are listed.

## Artifact Directory

All rerun evidence is in `artifacts/full-system-rerun-2026-06-25/`.
