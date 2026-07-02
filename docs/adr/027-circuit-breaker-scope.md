# ADR-027: Circuit-Breaker Scope

## Status

**Decided** (2026-07-02) — The healing circuit breaker is re-scoped from a single in-memory per-instance object to a **layered model: per-provider/model + per-run**, with state persisted in **Redis** so it is correct under the multi-instance production target (PostgresSaver). A **global** breaker is explicitly rejected. Companion to ADR-026 and the Phase-0 gate of the agents-hardening roadmap. Resolves the circuit-breaker scope question of Verdict 05.

## Context

`packages/agents/healing/circuit_breaker.py` today is a single `CircuitBreaker` with one `threshold`/`recovery_timeout` from `GateConfig`, holding `self.failures`/`self.state` **in memory on the instance**. It has no notion of `run_id`, `teacher_id`, or provider/model.

Two problems, both confirmed against code:

1. **Undefined blast radius.** Because scope is implicit (per-instantiation), it is unclear what tripping the breaker actually protects — and whether one pathological run (e.g. an over-long artifact repeatedly failing) can trip a breaker that then blocks unrelated teachers.
2. **Multi-instance incorrectness.** The production target runs multiple gateway instances with `PostgresSaver` checkpoints (ARCHITECTURE.md §10.6). In-memory breaker state is per-process, so N instances see N independent, inconsistent breakers — the breaker cannot reliably detect a provider outage across the fleet, nor consistently isolate a run.

The gateway already fronts LLM calls with **LiteLLM Proxy (L1, fallback chains) → 9Router (L2)**, which has its own provider-fallback concept — so a naïve provider breaker in `packages/agents` risks duplicating LiteLLM logic.

## Decision

### 1. Layered scope, not a single breaker

- **Provider/model breaker** — trips per upstream provider/model (Kiro / OpenCode / Vertex, etc.). Its job is to detect an upstream outage and stop hammering a dead provider. It **coordinates with**, and does not duplicate, the LiteLLM fallback chain: `packages/agents` consumes LiteLLM's health/fallback signal where available rather than re-implementing provider rotation. Where `packages/agents` must own it, the boundary is documented so the two layers don't fight.
- **Run breaker** — trips per `run_id`, isolating a single pathological run so it cannot affect other teachers' runs. This is the isolation guarantee the current design lacks.

### 2. Global breaker rejected

A single system-wide breaker is rejected: one individual bad run (over-long artifact, poisoned input) could trip it and block **every** teacher — an unacceptable blast radius for a multi-tenant K-12 product.

### 3. State persisted in Redis (multi-instance safe)

Breaker counters/state move from in-process fields to **Redis** (already in the stack for LiteLLM cache + shared state, ARCHITECTURE.md §1), keyed by scope (`cb:provider:<model>`, `cb:run:<run_id>`), so all gateway instances share one consistent view. Config (`threshold`, `recovery_timeout`) stays in `GateConfig`; only the *state* moves to Redis.

### 4. Escalation and observability

A tripped breaker is not a silent dead-end: it emits an `ObservabilityEvent` (Verdict 06) and, for a run breaker exhaustion, routes to the escalate path (→ teacher gate with notification, per ADR-026 / Verdict 07). Ops dashboard surfaces breaker trips per provider and per day.

## Consequences

- The breaker becomes correct under multi-instance production instead of silently per-process.
- One bad run can no longer block unrelated teachers (run isolation); a real provider outage is detected fleet-wide (provider scope).
- Adds a Redis dependency on the healing hot path — must be resilient to Redis being unavailable (fail-open on breaker read is acceptable: absence of breaker state means "closed/allow", never "block"), and must not duplicate LiteLLM's provider rotation.
- Belongs to Phase 4 (resilience) of the roadmap, but the **scope decision is made now (Phase 0)** so Phase 4 implementation builds on a settled model rather than re-litigating it mid-build.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| **Layered per-provider + per-run, Redis-backed (chosen)** | Correct multi-instance; run isolation; provider-outage detection; coordinates with LiteLLM | More moving parts; Redis dependency on healing path |
| Global single breaker | Simplest; fast outage detection | One bad run blocks all teachers — unacceptable blast radius |
| Keep in-memory per-instance | No new dependency | Broken under multi-instance production; undefined scope |
| Delegate entirely to LiteLLM/9Router, drop breaker in `packages/agents` | No duplicate logic; simplest for agents | Loses per-`run_id` isolation LiteLLM cannot express; documented as known gap |
