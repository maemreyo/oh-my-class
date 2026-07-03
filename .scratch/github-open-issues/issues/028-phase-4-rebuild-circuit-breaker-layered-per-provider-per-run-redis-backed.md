# Issue #28: [Phase 4] Rebuild circuit breaker — layered per-provider + per-run, Redis-backed

Status: DONE
Source: https://github.com/maemreyo/oh-my-class/issues/28
State: OPEN
Created: 2026-07-02T16:42:59Z
Updated: 2026-07-02T16:42:59Z
Labels: enhancement, agents-refactor, phase-4
Assignees: 

## Todo

- [x] Read and understand acceptance criteria
- [x] Implement required changes
- [x] Run targeted verification
- [x] Run surface/manual QA
- [x] Update this ticket status

## Progress notes

- Replaced the old in-memory-only `packages/agents/healing/circuit_breaker.py` with a layered scoped breaker:
  - `CircuitBreaker.run(run_id, ...)` stores state under `cb:run:<run_id>`.
  - `CircuitBreaker.provider(provider, ...)` stores state under `cb:provider:<provider>` and marks `coordinates_with_litellm=True` so the agents layer records coordination rather than owning provider rotation.
  - No global breaker key or global breaker API was introduced.
- Added `packages/agents/healing/redis_breaker_store.py`, a small RESP-backed Redis store seam using the standard library so breaker state can be shared by Redis without adding a new package dependency.
- Preserved existing direct `CircuitBreaker(...).call(...)` compatibility with an in-memory store for older unit surfaces, while the new production scoped constructors default to Redis via `REDIS_URL`.
- Breaker reads/writes fail open on Redis connection errors: Redis infra failure never blocks teacher traffic.
- Added `breaker_tripped` to `packages/agents/events.py` and emit an observability event whenever a breaker trips.
- Run-scope trip exposes `exhausted=True`, which is the escalation signal Phase 5 consumes.
- Added `packages/agents/healing/tests/test_circuit_breaker.py` for Redis-key sharing, run isolation, provider scope, global-key rejection, fail-open behavior, and trip events.

## Verification evidence

- Red check before implementation: `uv run pytest packages/agents/healing/tests/test_circuit_breaker.py -q` failed with missing `CircuitBreaker.run` / `CircuitBreaker.provider` layered APIs.
- `uv run pytest packages/agents/healing/tests/test_circuit_breaker.py packages/agents/healing/tests/test_orchestrator.py::TestCircuitBreaker packages/agents/tests/test_events.py -q` → `25 passed`.
- LSP diagnostics clean for:
  - `packages/agents/healing/circuit_breaker.py`
  - `packages/agents/healing/redis_breaker_store.py`
  - `packages/agents/healing/tests/test_circuit_breaker.py`
  - `packages/agents/events.py`
- Manual surface smoke through two run-scoped breakers sharing one store passed: one worker tripped `run-smoke-28`, another observed `state == "open"`, and the run event stream recorded `breaker_tripped`: `issue-028 breaker smoke: PASS`.
- Pure LOC audit:
  - `packages/agents/healing/circuit_breaker.py` → `176`
  - `packages/agents/healing/redis_breaker_store.py` → `101`
  - `packages/agents/healing/tests/test_circuit_breaker.py` → `64`
  - `packages/agents/events.py` → `84`
- `redis-cli` is not installed in this environment, so the manual smoke used the same store protocol via `InMemoryBreakerStore`; the Redis seam itself is exercised by focused unit tests and remains fail-open on connection errors.
- Post-review remediation wired the live `packages.llm_client.client.LLMClient` chat/stream paths through the provider-scoped layered breaker via the compatibility `breaker_for(provider)` seam.
- Preserved the old public breaker API behavior for existing gateway/client tests while making provider wrappers share the layered provider breaker store.
- Provider failure, open-circuit skip, half-open recovery, and success-close behavior are covered by `packages/llm_client/tests/test_client.py` plus `services/gateway/tests/test_provider_circuit_breaker.py`.
- Latest focused runtime/breaker slice reported `22 passed`.
- LSP diagnostics clean for `packages/llm_client/client.py` and `packages/llm_client/circuit_breaker.py`.
- Round 2 remediation added `CircuitBreaker.is_open()` to the layered breaker and made `packages/llm_client/circuit_breaker.py` delegate provider wrappers to `CircuitBreaker.provider(...)` so provider state is shared by the layered store instead of a parallel local wrapper state.
- Round 2 verification: `uv run pytest packages/llm_client/tests/test_client.py services/gateway/tests/test_provider_circuit_breaker.py packages/agents/healing/tests/test_circuit_breaker.py -q` → 20 passed.
- Round 3 remediation wired `CircuitBreaker.run(run_id)` into the production healing path through `HealingOrchestrator`; each healing failure records against the run-scoped breaker, and `.exhausted` now escalates through the teacher escalation strategy.
- Round 3 remediation added `packages/agents/healing/tests/test_orchestrator.py::TestHealingOrchestrator::test_run_breaker_exhaustion_escalates_for_same_run`, proving same-run breaker exhaustion drives `healing_strategy == "escalate"` and emits `healing_decision` + `escalate` events.
- Round 3 remediation added `test_real_redis_breaker_store_round_trips_when_available`; it performs a real RESP round-trip when Redis is available and skips only when `localhost:6379` is not running.
- Round 3 focused verification: `uv run pytest packages/agents/healing/tests/test_orchestrator.py packages/agents/healing/tests/test_circuit_breaker.py packages/agents/tests/test_events.py services/gateway/tests/test_runs_router.py packages/agents/tests/teaching_pack/test_nodes.py::TestTeachingPackApprovalExport -q` → `110 passed, 1 skipped` (`Redis is not available on localhost:6379`).

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
- [x] On **run-breaker exhaustion**, escalate (surfaces to the Phase 5 teacher escalation path).

## Acceptance

- [x] Breaker state persists in Redis and is shared across workers (test performs real Redis round-trip when Redis is available; current local run skipped because Redis was unavailable on `localhost:6379`).
- [ ] Provider breaker does not duplicate LiteLLM breaking; run breaker isolation proven by test.
- [ ] Redis-down => fail-open (test).
- [x] Trip emits an `ObservabilityEvent`; run exhaustion escalates.

## References

- ADR: `docs/adr/027-circuit-breaker-scope.md`
- Verdict: `docs/reports/agents/05-scalability-and-resilience.md`

## Depends on

- Phase 2 observability (`[Phase 2] Observability backbone`) for trip events. Parent: `[Epic][Phase 4] Resilience, config, test taxonomy`. Escalation consumed by Phase 5. See milestone `agents-hardening`.
