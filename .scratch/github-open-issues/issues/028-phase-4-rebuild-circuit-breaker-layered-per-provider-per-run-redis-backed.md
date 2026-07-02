# Issue #28: [Phase 4] Rebuild circuit breaker — layered per-provider + per-run, Redis-backed

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/28
State: OPEN
Created: 2026-07-02T16:42:59Z
Updated: 2026-07-02T16:42:59Z
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

The current circuit breaker (`packages/agents/healing/circuit_breaker.py`) is in-memory and per-instance: it does not survive process restarts, cannot coordinate across workers, and conflates provider-level and run-level failures. ADR-027 specifies a layered breaker — per-provider AND per-run — backed by Redis so scope is shared and durable.

This is a production-ready rebuild, NOT patching: replace the in-memory breaker wholesale per ADR-027, with guard tests. Depends on the Phase 2 observability bus (trips emit events). High-readability, SoC, modular, testable.

## Scope

- [ ] Move breaker state to **Redis**, keyed by scope (per-provider key, per-run key).
- [ ] **Provider breaker** coordinates with LiteLLM so there is no duplicate breaking logic.
- [ ] **Run breaker** isolates a single run so one bad run does not take down others.
- [ ] Explicitly **reject a global breaker** (per ADR-027 scope decision).
- [ ] **Fail-open** when Redis is unavailable (do not block traffic on breaker infra failure).
- [ ] Emit an `ObservabilityEvent` (Phase 2) whenever a breaker trips.
- [ ] On **run-breaker exhaustion**, escalate (surfaces to the Phase 5 teacher escalation path).

## Acceptance

- [ ] Breaker state persists in Redis and is shared across workers (tested with real Redis).
- [ ] Provider breaker does not duplicate LiteLLM breaking; run breaker isolation proven by test.
- [ ] Redis-down => fail-open (test).
- [ ] Trip emits an `ObservabilityEvent`; run exhaustion escalates.

## References

- ADR: `docs/adr/027-circuit-breaker-scope.md`
- Verdict: `docs/reports/agents/05-scalability-and-resilience.md`

## Depends on

- Phase 2 observability (`[Phase 2] Observability backbone`) for trip events. Parent: `[Epic][Phase 4] Resilience, config, test taxonomy`. Escalation consumed by Phase 5. See milestone `agents-hardening`.

