# [VER-02] Test-taxonomy enforcement + tiered CI cadence
Status: TODO
Labels: verification, ci
ADR: 032
Depends on: none

## Context
ADR-032 Decision 2 requires the test taxonomy to be "real and tiered" —
placement enforced into `tests/{guard,contract,unit,integration,e2e,resilience,security}/`,
each tier with a `make` target, and a two-speed CI: a fast **merge gate** on every PR and
a slow **release gate** nightly/pre-deploy.

Today the taxonomy is scaffolding, not enforced:

- The tier directories exist but are empty placeholders:
  `tests/guard/.gitkeep`, `tests/contract/.gitkeep`, `tests/unit/.gitkeep`,
  `tests/resilience/.gitkeep`. `tests/security/` has real content;
  `tests/integration/` and `tests/e2e/` exist (the latter has its own `conftest.py`).
- The bulk of the ~453+ Python tests live in old locations, not in the taxonomy:
  `packages/agents/tests/`, `packages/quality/tests/`, `common/contracts/tests/`,
  `services/gateway/` tests, and flat files directly under `tests/` (e.g.
  `tests/test_invariant_coverage.py`, `tests/test_parked_status_ttl.py`).
- CI runs one undifferentiated Python test step. `.github/workflows/ci.yml` `test-python`
  invokes `pytest --tb=short` over everything plus a few coverage-gated subdirs; there is
  no fast-vs-slow split, so slow e2e/resilience work either blocks every PR or (worse)
  does not run at all. `make test` (Makefile) likewise runs one flat pytest invocation
  over `packages/agents packages/quality common/contracts services/gateway tests/`.
- There is no `make test-<tier>` target and nothing prevents a new test from landing in
  the wrong tier (e.g. an LLM-driven e2e test dropped into `tests/unit/` where it slows
  the merge gate).

VER-03 (safety adversarial/mutation) and VER-04 (merge-vs-release CI contract doc) both
build on this tiered structure, so this issue establishes it first.

Principle: production-ready, not a patch. Establish the tiers as enforced structure with
guard tests, and migrate incrementally under an explicit, tracked policy rather than a
risky one-shot move of 453 files.

## Scope
- [ ] Define the canonical tier set and their semantics in one place (a docstring/registry,
  e.g. `tests/TAXONOMY.md` or a `tests/_taxonomy.py` constant): guard, contract, unit,
  integration, e2e, resilience, security — with a one-line rule for what belongs in each
  and which gate (merge/release) runs it.
- [ ] Add `make test-<tier>` targets for each tier (`test-guard`, `test-contract`,
  `test-unit`, `test-integration`, `test-e2e`, `test-resilience`, `test-security`) plus
  `make test-merge` (fast composite) and `make test-release` (slow composite). Update the
  Makefile `.PHONY` list accordingly.
- [ ] Add a placement-enforcement guard test under `tests/guard/` that fails if a test
  file lands outside the taxonomy or is mis-tiered by an objective signal (e.g. a test
  marked `@pytest.mark.e2e` or importing the FFA-10 driver / real-LLM fixtures must live
  under `tests/e2e/`; a test importing `hypothesis` or marked `property` for a safety
  invariant belongs under `tests/security/` per VER-03). Register pytest markers for each
  tier in `pyproject.toml` (the `property` marker already exists there under
  `[tool.pytest.ini_options] markers`).
- [ ] Define the **merge gate** composite = unit + contract + guard + security + schema
  parity (`make check-schemas`) + invariant-coverage meta-test
  (`tests/test_invariant_coverage.py`) + live-path proof (VER-01) + boundary/lint
  (`lint-imports`, `depcruise`) + new-component-test policy. It must be fast (no real LLM,
  no full-output matrix).
- [ ] Define the **release gate** composite = full e2e (FFA-10 driver, real LLM via
  9router :20228, model 4omc), resilience, and the ADR-031 full-output matrix. Run as a
  scheduled nightly workflow and as a pre-deploy job.
- [ ] Split `.github/workflows/ci.yml`: make the PR-triggered job run `make test-merge`
  (fast); add a `schedule:`-triggered workflow (or job) running `make test-release`.
- [ ] Write the incremental migration policy for the ~453 existing tests: new/changed
  tests MUST land in a taxonomy tier; a tracked, shrinking allowlist grandfathers the old
  locations; each migrated batch moves files into the correct tier and updates the pytest
  invocation. Do NOT big-bang-move all 453 at once (breaks blame/coverage gates); big-bang
  applies to the *enforcement mechanism*, incremental applies to *file relocation*.

## Acceptance
- `make test-guard`, `test-contract`, `test-unit`, `test-integration`, `test-e2e`,
  `test-resilience`, `test-security`, `test-merge`, `test-release` all exist and run only
  their tier's tests.
- Adding a new test file outside `tests/{guard,contract,unit,integration,e2e,resilience,security}/`
  (excluding the grandfather allowlist) fails the placement guard test with a message
  naming the offending path and the tier it should go in.
- Adding an e2e/real-LLM test into `tests/unit/` fails the mis-tier guard test.
- The PR CI job runs the merge-gate composite and does NOT invoke real-LLM/e2e/resilience;
  a separate scheduled workflow runs the release-gate composite.
- The migration allowlist is a single tracked file; removing an entry and not moving the
  file causes CI to fail (proving the allowlist actually gates).
- Existing green tests still pass after the tiering scaffolding lands (no coverage-gate
  regressions in `packages/agents` ≥85, `common/contracts` ≥95, `packages/quality` ≥90).

## References
- ADR-032 (Decision 2: real tiered taxonomy, merge gate vs release gate)
- `tests/guard/.gitkeep`, `tests/contract/.gitkeep`, `tests/unit/.gitkeep`,
  `tests/resilience/.gitkeep` (empty scaffolding to fill)
- `tests/security/` (already populated), `tests/e2e/conftest.py`, `tests/integration/`
- `tests/test_invariant_coverage.py`, `tests/test_parked_status_ttl.py` (flat tests to
  migrate)
- `packages/agents/tests/`, `packages/quality/tests/`, `common/contracts/tests/` (~453
  tests in old locations)
- `Makefile` (`test`, `test-python`, `test-integration` targets; `.PHONY` list)
- `.github/workflows/ci.yml` `test-python` job (single flat pytest to split)
- `pyproject.toml` `[tool.pytest.ini_options] markers` (already has `property` marker)

## Implementation notes
- Enforce placement objectively, not by intent-guessing. Good signals: pytest markers,
  imports of the FFA-10 e2e driver, imports of real-LLM/DB fixtures, `hypothesis` import.
  Keep the rule table small and documented; a test that matches no signal defaults to the
  tier implied by its directory, and the guard only fails on *contradictions* (marker says
  e2e, directory says unit).
- Tests are real, not mock in this repo: e2e/integration use a real DB and real LLM
  (9router :20228, model 4omc). Keep those strictly in the release gate so the merge gate
  stays fast and hermetic — do not let a "unit" test reach the network.
- The FFA-10 full-artifact-array e2e driver and the ADR-031 full-output matrix are the
  heavy release-gate items; wire them behind `make test-release` / the scheduled workflow,
  not the PR path.
- Verify the live path of the gate itself: after adding targets, run each `make test-<tier>`
  locally and confirm it collects a non-empty, tier-appropriate set (a `make test-e2e`
  that silently collects 0 tests is a hollow gate — assert non-empty collection in the
  guard test or via `pytest --collect-only` count).
- Migration ordering: move the flat `tests/test_*.py` invariant/meta tests into
  `tests/guard/` or `tests/contract/` first (small, high-signal), then per-package batches.
