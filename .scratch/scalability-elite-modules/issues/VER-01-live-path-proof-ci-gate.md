# [VER-01] Live-path-proof CI gate (CodeGraph-powered) + ban tautological tests
Status: TODO
Labels: verification, ci
ADR: 032
Depends on: none

## Context
ADR-032 names the system's #1 maturity risk as "green but hollow": tests pass while
the runtime path is broken. Concrete instances found across 4 review rounds include a
capability registry with no caller, a revert UI that was unreachable, and a dead
`escalate` route — all while their unit tests stayed green.

The current new-component gate is bypassable by design. `scripts/verify_new_component_tests.py`
proves a *file exists*, not that the module is *reached at runtime*:

- `packages/agents/testing/verify_new_component_tests.py` matches a component to a test
  purely by filename stem: `_test_matches_component` (line 65-66) compares
  `_normalized_module_stem(test_path) == added.module_stem` (line 69-70). Any file named
  `test_<stem>.py` satisfies the gate even if it never imports, calls, or reaches the
  component. A test that only asserts `True` passes the gate.
- The whole check no-ops off-CI: `_merge_base()` returns `None` when `GITHUB_BASE_REF`
  is unset (line 90-100), and while `_policy_paths()` (line 103-119) still computes a
  diff against `HEAD` locally, the gate is effectively only meaningful on PRs and is
  trivially satisfied by any co-named file.
- Tautological tests are unguarded. `tests/security/test_security_stubs.py` is the
  canonical example: `test_answer_key_not_in_student_html` asserts markers are absent
  from a hardcoded literal string it wrote itself; `test_gate_bypass_requires_auth`
  asserts on a dict literal it constructed; `test_promptfoo_security_suite_invokes_eval_command`
  mocks the very `subprocess.run` it claims to verify. None touch production code.

CodeGraph is indexed at `.codegraph/` (49MB SQLite graph, `codegraph explore`/`codegraph
callers`/`codegraph node` CLI + MCP). It can answer reachability deterministically from
the compiled graph and router handlers — turning "does a live path invoke this module?"
into a graph query instead of a filename guess. The production entrypoints to anchor
reachability from are concrete: the compiled LangGraph at
`packages/agents/teaching_pack/graph.py:132` (`graph.compile(...)`, with nodes added at
lines 54-56, 72-83) and the FastAPI routers under `services/gateway/routers/` (e.g.
`runs.py`, `teaching_pack_runs.py`, `approvals.py`).

Principle: production-ready, not a patch. Big-bang replacement of the substring matcher
with a reachability proof, shipped with guard tests. Live-path proof over coverage-%.

## Scope
- [ ] Add a CodeGraph reachability adapter module (e.g.
  `packages/agents/testing/live_path.py`) that shells out to `codegraph` (or queries
  `.codegraph/codegraph.db` directly) and exposes: `reachable_from_roots(module_symbol) -> bool`
  and `callers(symbol) -> list[str]`. Fail closed (raise) if `.codegraph/` is missing or
  the index is stale relative to `git HEAD` — never silently pass. Cite fail-closed policy
  per repo convention (fail-closed vs silent degradation).
- [ ] Define the reachability root set explicitly in one place (a `LIVE_PATH_ROOTS`
  constant): the compiled graph builder `build_teaching_pack_graph` and every node it
  registers (`packages/agents/teaching_pack/graph.py:32,54-56,72-83`), plus every FastAPI
  route handler discovered under `services/gateway/routers/`. Document how a new agent
  graph or router is added to the root set.
- [ ] Rewrite `scripts/verify_new_component_tests.py`: replace `_test_matches_component`
  filename-stem logic (line 65-70) with a two-part proof per added production component:
  (a) the component symbol is reachable from a `LIVE_PATH_ROOTS` root in the call graph;
  (b) at least one test exercises that live path (imports the root/graph and drives it,
  not just imports the component in isolation). A module that is reachable but has no
  live-path test fails; a module with a test but no reachability edge fails as "dead
  code / hollow test".
- [ ] Add a tautology detector as a separate lint pass (e.g.
  `scripts/verify_no_tautological_tests.py`): flag test functions that (1) assert only on
  literals defined within the same function and never import/call any `packages/`,
  `services/`, `common/`, or `apps/` production symbol; and (2) "registry fed back to
  itself" — a test that both constructs/imports a registry and asserts a property derived
  from that same registry with no independent expectation (e.g. `assert set(REGISTRY_IDS)
  == set(REGISTRY_IDS)` shaped checks). Seed the detector's fixtures from the known
  offender `tests/security/test_security_stubs.py`.
- [ ] Wire both scripts into the merge gate in `.github/workflows/ci.yml` `test-python`
  job (which already runs `python scripts/verify_new_component_tests.py`), adding a
  CodeGraph index build/sync step (`codegraph sync` or `codegraph index`) before the gate
  so `.codegraph/` is present and fresh in CI.
- [ ] Provide an allowlist mechanism (small, reviewed, with expiry/reason) for the
  in-progress migration so the big-bang switch does not block unrelated PRs on day one —
  but the allowlist must itself be a tracked file, not an env-var escape hatch.

## Acceptance
- A PR adding a production module that is *not* reachable from any `LIVE_PATH_ROOTS` root
  fails CI with a message naming the module and the roots it was checked against.
- A PR adding a reachable module whose only test imports it in isolation (no live-path
  drive) fails CI; adding a test that drives it via the graph/router makes CI pass.
- Re-introducing a dead route (delete the `escalate`/revert wiring) causes the gate to
  flag the now-unreachable handler — verified by a guard test that removes an edge and
  asserts the gate reports it.
- The tautology detector flags every function in `tests/security/test_security_stubs.py`
  as tautological/hollow, and passes clean on a real live-path test (e.g.
  `tests/security/test_answer_key_leakage.py` which imports and calls `_compliance_gate`).
- The gate fails closed: with `.codegraph/` absent or stale, CI errors loudly rather than
  returning 0.
- Guard tests for the new logic live under `tests/guard/` and cover: reachable+tested
  (pass), reachable+untested (fail), unreachable (fail), stale-index (error),
  tautological test (flagged).

## References
- ADR-032 (Decision 1: live-path proof is a hard CI gate; ban tautological tests)
- `scripts/verify_new_component_tests.py:65-70` (substring matcher to replace),
  `:90-100` (`GITHUB_BASE_REF` no-op), `:103-119` (`_policy_paths`)
- `packages/agents/teaching_pack/graph.py:32,54-56,72-83,132` (compiled graph roots)
- `services/gateway/routers/` (router handler roots: `runs.py`, `teaching_pack_runs.py`,
  `approvals.py`, ...)
- `tests/security/test_security_stubs.py` (canonical tautological/hollow tests)
- `tests/guard/test_new_component_tests_policy.py` (existing policy guard tests to extend)
- `.github/workflows/ci.yml` `test-python` job (wire-in point)
- `.codegraph/codegraph.db`; `codegraph explore|callers|node|sync|index` CLI

## Implementation notes
- Prefer the `codegraph` CLI (`codegraph callers <symbol>`, `codegraph node <symbol>`) for
  a stable text contract over reading the SQLite schema directly; the DB schema is an
  internal detail and may change. If performance requires direct DB reads, isolate SQL in
  the adapter so the rest of the gate is schema-agnostic.
- LangGraph nodes are registered by string name via `graph.add_node(stage.value,
  make_stage_node(...))` (`graph.py:55`). Reachability from the *string* node name to the
  Python callable goes through `make_stage_node`/`make_stage_node`-produced closures in
  `packages/agents/teaching_pack/nodes.py`; the adapter must resolve these factory-produced
  handlers, not just literal `def`-level edges. This dynamic-dispatch hop is exactly what
  CodeGraph follows and grep cannot — lean on it.
- "Live-path test" detection: a heuristic that a test drives a root (imports
  `build_teaching_pack_graph` and invokes/compiles it, or calls a router handler / uses
  FastAPI `TestClient`) is more robust than trying to prove a runtime call statically.
  Keep the heuristic explicit and documented; false-negatives should fail closed.
- Verify live-path proof end-to-end, not just unit-of-the-gate: in CI, after building the
  index, run the gate against the current HEAD and confirm it passes on the real repo
  (all currently-shipped modules are reachable or allowlisted), then run it against a
  synthetic branch that adds a dead module and confirm it fails.
- Do not chase coverage-%. A module at 100% line coverage but unreachable from a root must
  still fail — that is the whole point.
