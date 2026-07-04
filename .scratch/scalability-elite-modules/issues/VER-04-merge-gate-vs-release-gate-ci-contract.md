# [VER-04] Merge-gate vs release-gate CI contract doc
Status: TODO
Labels: verification, ci
ADR: 032
Depends on: VER-01, VER-02

## Context
ADR-032 Decision 2 defines two distinct CI cadences — a fast **merge gate** on every PR and
a slow **release gate** nightly/pre-deploy — but the exact contract (what is "green to
merge" vs "green to release") lives only in the ADR prose and is not written down where
contributors look, nor wired consistently into CI config.

Concrete state:

- `.github/workflows/ci.yml` currently mixes fast and slow checks in one PR-triggered set
  of jobs (typecheck, import lint, dep-cruise, schema parity, `test-python`,
  `test-typescript` incl. Playwright e2e, docker build). There is no documented distinction
  between "must be green to merge" and "must be green to release", and no
  `schedule:`-triggered release job (VER-02 introduces one).
- There is no single CONTRIBUTING/CI doc enumerating the gate contents. A contributor
  cannot tell, before pushing, which checks block their merge vs which run later.
- The ADR lists the merge-gate members (unit + contract + guard + security + schema parity
  + invariant-coverage meta-test + live-path proof + boundary/lint + new-component-test
  policy) and the release-gate members (full e2e via FFA-10 driver + real LLM, resilience,
  ADR-031 full-output matrix), but nothing keeps the doc and the CI config from drifting.

This depends on VER-01 (live-path proof gate must exist to be listed as a merge-gate member)
and VER-02 (the tiered `make test-<tier>` targets and the split merge/release workflows must
exist to be documented and wired).

Principle: production-ready, not a patch. The doc is the single source of truth for the CI
contract and is mechanically kept in sync with the workflow config.

## Scope
- [ ] Author one CI-contract document (e.g. `CONTRIBUTING.md` section or `docs/ci-contract.md`)
  that lists, explicitly and exhaustively:
  - **Green to merge (merge gate, every PR, fast):** unit, contract, guard, security
    (fast subset), schema parity (`make check-schemas`), invariant-coverage meta-test
    (`tests/test_invariant_coverage.py`), live-path proof (VER-01
    `scripts/verify_new_component_tests.py` reachability + tautology detector),
    boundary/lint (`lint-imports`, `depcruise`, `ruff`, `bash scripts/typecheck.sh`),
    new-component-test policy.
  - **Green to release (release gate, nightly + pre-deploy, slow):** full e2e (FFA-10
    driver, real LLM via 9router :20228 / model 4omc), resilience, ADR-031 full-output
    matrix.
  - For each entry: the `make` target / script that runs it, roughly how long it takes,
    and why it sits in that tier.
- [ ] Wire the doc into CI config so the two workflows exactly realize it: the PR job runs
  `make test-merge`; the scheduled/pre-deploy job runs `make test-release` (both from
  VER-02).
- [ ] Add a drift guard: a test/script asserting the CI-contract doc and the workflow
  config list the same gate members (parse the enumerated list from the doc and compare to
  the steps the workflows invoke, or drive both from a shared manifest). Prevents the doc
  and `.github/workflows/*.yml` from silently diverging.
- [ ] Cross-link the doc from ADR-032 and from the taxonomy doc introduced in VER-02.

## Acceptance
- A single doc enumerates every merge-gate and release-gate member with its runner and
  tier rationale; a contributor can determine pre-push exactly what blocks their merge.
- The PR workflow invokes only merge-gate members (no real-LLM/e2e/resilience); the
  scheduled/pre-deploy workflow invokes the release-gate members.
- The drift guard fails if a gate member is added to CI config but not the doc (or vice
  versa) — verified by adding a step to the workflow without updating the doc and seeing
  the guard fail.
- The doc is referenced from ADR-032 and the VER-02 taxonomy doc.

## References
- ADR-032 (Decision 2: merge gate vs release gate membership)
- `.github/workflows/ci.yml` (current single-cadence jobs to split/realize)
- VER-01 (`scripts/verify_new_component_tests.py` live-path proof + tautology detector) —
  merge-gate member
- VER-02 (`make test-merge` / `make test-release` targets and split workflows)
- `tests/test_invariant_coverage.py`, `make check-schemas`, `lint-imports`,
  `.dependency-cruiser.cjs`, `scripts/typecheck.sh` (named merge-gate members)

## Implementation notes
- Prefer a shared manifest (e.g. a small YAML/py list of gate members with `tier`, `runner`,
  `est_seconds`) that both the doc-generation and the workflow reference, so the drift guard
  compares against one source rather than parsing free-form Markdown. If a manifest is too
  heavy, at minimum make the doc's gate table machine-parseable (fenced, stable columns) so
  the guard can diff it against the workflow steps.
- Keep the doc terse and operational — it is a contract, not a tutorial. Times can be
  approximate but should make the fast/slow split self-evident.
- Verify the live path: after wiring, trigger the PR workflow on a trivial change and
  confirm it runs exactly the merge-gate set; trigger the scheduled workflow manually
  (`workflow_dispatch`) and confirm it runs the release-gate set.
