# Issue #23: [Phase 2] Observability backbone — ObservabilityEvent, run_events table, INVARIANT_REGISTRY

Status: TODO
Source: https://github.com/maemreyo/oh-my-class/issues/23
State: OPEN
Created: 2026-07-02T16:42:36Z
Updated: 2026-07-02T16:42:36Z
Labels: enhancement, agents-refactor, phase-2
Assignees: 

## Todo

- [ ] Read and understand acceptance criteria
- [ ] Implement required changes
- [ ] Run targeted verification
- [ ] Run surface/manual QA
- [ ] Update this ticket status

## Body

## Context

The system has no real observability backbone. There is no typed event, no durable event store, and no registry that ties invariants to tests. This blocks both ops visibility and the Phase 5 teacher live-status. Critically, ops and the teacher UI must be fed from the **same** stream — building two pipelines would guarantee they diverge.

This is a production-ready rebuild, NOT patching: `events.py` becomes a real bus, backed by a typed event and a Postgres table. High-readability, SoC, modular, testable.

## Scope

- [ ] Define `ObservabilityEvent` as a Pydantic model (typed fields, `Literal` for event kinds, `Field` bounds where relevant, `default_factory` for timestamps/ids).
- [ ] Turn `events.py` into a real event bus (publish/subscribe), not a stub.
- [ ] Add a Postgres `run_events` table + a writer that persists every `ObservabilityEvent`.
- [ ] Build `INVARIANT_REGISTRY` (one entry per invariant) and a meta-test `test_invariant_coverage.py` that fails if any registered invariant lacks a corresponding test.
- [ ] Make this stream the **single** shared source for the ops dashboard AND the Phase 5 teacher live-status — do not build two pipelines.

## Acceptance

- [ ] `ObservabilityEvent` model + `run_events` writer land with real DB tests (real Postgres, not mocked).
- [ ] Events published on the bus are persisted to `run_events` and readable by a single downstream consumer.
- [ ] `test_invariant_coverage.py` passes and fails when an invariant has no test.

## References

- ADR: `docs/adr/027-circuit-breaker-scope.md` (breaker events feed this bus)
- Verdict: `docs/reports/agents/06-testing-and-observability-strategy.md`

## Depends on

- `[Epic][Phase 2] State unification + observability backbone` (parent). Consumed by Phase 4 (breaker events) and Phase 5 (teacher live-status). See milestone `agents-hardening`.

