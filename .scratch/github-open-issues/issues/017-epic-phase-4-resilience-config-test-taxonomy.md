# Issue #17: [Epic][Phase 4] Resilience, config, test taxonomy

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/17
State: OPEN
Created: 2026-07-02T16:42:11Z
Updated: 2026-07-02T16:42:11Z
Labels: enhancement, agents-refactor, phase-4
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

With state, judge, compliance and harness consolidated, the system needs to be made resilient and its testing put on a durable footing. This epic covers rebuilding the circuit breaker per ADR-027, provider fallback/health, streaming-interruption resilience, a real test taxonomy, and a "new component must ship with a test" CI policy. It depends on the Phase 2 observability backbone (breaker trips and health events flow through it) and on Phase 3 (the harness the resilience features hang off).

**Already done — do not create work for it:** the artifact parallelism cap is ALREADY config-driven via `TeachingPackConfig().default_artifact_parallelism`. This epic only records that it is done; there is no "move parallelism to config" task.

This is a production-ready rebuild, NOT patching. The breaker rebuild replaces the in-memory per-instance breaker (`packages/agents/healing/circuit_breaker.py`) wholesale, with guard tests, high readability, SoC, modular, testable.

## Scope

Child issue (separate in this milestone):

- [ ] Rebuild circuit breaker — layered per-provider + per-run, Redis-backed (per ADR-027).

In-body checklist for the rest of Phase 4:

- [ ] 9Router fallback + health-check: detect provider degradation and route around it.
- [ ] Streaming-interruption resilience test for the Content Creator agent (simulate a dropped stream mid-generation, assert graceful recovery).
- [ ] Establish test taxonomy directories: `guard/`, `contract/`, `unit/`, `integration/`, `e2e/`, `resilience/`.
- [ ] CI policy: **every new component must ship with a test** (fail the build otherwise).
- [ ] 10/10 invariant tests present and green (ties to `INVARIANT_REGISTRY` meta-test from Phase 2).
- [ ] Record that artifact parallelism cap is already config-driven (`TeachingPackConfig().default_artifact_parallelism`) — no action needed.

## Acceptance

- [ ] Circuit-breaker child issue closed with tests.
- [ ] Streaming-interruption resilience test passes.
- [ ] Test taxonomy dirs exist and CI enforces "new component ships with a test".
- [ ] All 10 invariant tests pass.

## References

- ADR: `docs/adr/027-circuit-breaker-scope.md`
- Verdict: `docs/reports/agents/05-scalability-and-resilience.md`, `docs/reports/agents/06-testing-and-observability-strategy.md`

## Depends on

- Phase 2 (`[Epic][Phase 2] State unification + observability backbone`) for the event bus, and Phase 3 (`[Epic][Phase 3] Core correctness`) for the shared harness. See milestone `agents-hardening`.

