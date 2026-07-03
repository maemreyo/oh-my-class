# [FFA-11] Retire stale legacy `/run` e2e scripts

Status: TODO
Labels: full-flow-api, cleanup, testing
ADR: —
Depends on: FFA-10 (replacement in place first)

## Context

`scripts/test_e2e_real_llm.py`, `scripts/test_full_flow.py`, and `scripts/run_e2e.sh` target
the LEGACY `/run`, `/run/{id}/approve`, `/run/{id}/artifacts` API — which now returns
HTTP 410 GONE (`services/gateway/routers/runs.py:228`, decommissioned per ADR-018).
`test_full_flow.py` is additionally mock-LLM and happy-path only. They are dead/misleading and
violate the "physical deletion + guard test" precedent.

## Scope

- [ ] After FFA-10 lands the replacement, delete `scripts/test_full_flow.py`,
      `scripts/test_e2e_real_llm.py`, and the legacy `scripts/run_e2e.sh` /
      `.scratch/api-test-output/run_live_flow.py` driver (or rewrite `run_e2e.sh` to invoke
      FFA-10's driver).
- [ ] Grep for any Make target / CI step referencing them; repoint to the new driver.
- [ ] Guard test / note asserting no script calls the decommissioned `/run` create/approve API.

## Acceptance

- No script in `scripts/` targets the 410 `/run` API.
- `make` targets and CI reference only the new `/teaching-packs/*` driver.

## References

- `runs.py:228` (410), ADR-018 (legacy decommission), FFA-10 (replacement).
  Stale: `scripts/test_full_flow.py`, `scripts/test_e2e_real_llm.py`, `scripts/run_e2e.sh`.
