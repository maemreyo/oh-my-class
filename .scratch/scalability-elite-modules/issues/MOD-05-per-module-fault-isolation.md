# [MOD-05] Per-module fault isolation (timeout + fail-closed boundary + circuit breaker)

Status: TODO
Labels: module-standard, reliability, agents
ADR: 033
Depends on: none

## Context

ADR-033 §Decision.5: modules run in-process, but each gets a per-module timeout + fail-closed
error boundary + circuit breaker (for LLM modules). Node exporter subprocesses are already
isolated. No microservice-per-module at mid-scale. The desired failure semantics: a module
error ⇒ healing / dependency-skip, NOT a worker crash.

The primitives already exist:

- Circuit breaker: `packages/llm_client/circuit_breaker.py` (`CircuitBreaker`,
  `breaker_for`, `should_skip_provider` at lines 92-99; states CLOSED/OPEN/HALF_OPEN;
  `failure_threshold=3`, `recovery_seconds=60`) delegating to
  `packages/agents/healing/circuit_breaker.py`. A second breaker exists at
  `packages/quality/layer1_schema/circuit_breaker.py`.
- Observability already has a `breaker_tripped` event type
  (`packages/agents/events.py:23-41`) and `step_failed` for fail paths.
- Healing orchestrator: `packages/agents/healing/orchestrator.py` (referenced by the grounding
  as the healing path) — the intended destination when a module fails rather than crashing.
- `AgentRuntime._call_once` (`packages/agents/runtime.py:152-196`) already logs
  start/success/failure and supports `backoff_seconds`, but has no timeout or breaker gate.
- The agent-wrapper skip policy is fail-closed (skip dependency / raise), not silent
  degradation — this issue generalizes that into a reusable boundary.

What is missing: a single reusable per-module fault boundary that wraps a module invocation
with (1) a timeout, (2) a fail-closed catch that routes to healing/dependency-skip, and (3)
a circuit breaker for LLM-backed modules — applied uniformly across families instead of each
node re-implementing try/except.

## Scope

- [ ] Implement a `ModuleFaultBoundary` (async context manager or decorator) in
      `packages/agents/` that wraps a module invocation with:
      - **timeout**: per-module configurable deadline (use `anyio` — `runtime.py` already
        imports `anyio`); on timeout, treat as a fail-closed error.
      - **fail-closed catch**: on any exception, emit `ObservabilityEvent`
        `step_failed` (`packages/agents/events.py:71-73`) and either (a) route to the healing
        orchestrator, or (b) mark the dependency skipped for downstream nodes — never let the
        exception crash the worker/graph process. The chosen policy is declared per module
        (healing vs. skip), matching the fail-closed default from MOD-01 point 5.
      - **circuit breaker (LLM modules)**: before invoking an LLM-backed module, check
        `should_skip_provider` / `breaker_for(provider).is_open()`
        (`packages/llm_client/circuit_breaker.py:92-99`); on open, short-circuit fail-closed
        and emit `breaker_tripped`; on success/failure, record via
        `record_success`/`record_failure`.
- [ ] Wire the boundary into `AgentRuntime` (or a thin wrapper around it) so agent modules get
      timeout + breaker without per-node code — extend `_call_once`
      (`packages/agents/runtime.py:152-196`) to run under the boundary and add
      `timeout_seconds` to `AgentRuntimeConfig` (`packages/agents/runtime.py:34-45`).
- [ ] Provide adapters so non-agent families (renderer plugin invocation, quality layer, gate)
      can run under the same boundary at their call sites, with per-family default policies
      (e.g. renderer failure ⇒ dependency-skip that artifact + gate-block; gate failure ⇒
      fail-closed block).
- [ ] Confirm Node exporter subprocesses remain the existing isolated path (do not double-wrap);
      document that they are already isolated per ADR-033.
- [ ] Emit the full event trio on the boundary: entry (`step_started`), success
      (`step_completed`), failure (`step_failed` / `breaker_tripped`) so MOD-01 point 4 is
      satisfied uniformly.

## Acceptance

- A module that raises inside the boundary does NOT crash the worker/graph: the run proceeds
  via healing or with the dependency marked skipped, and a `step_failed` event is emitted.
- A module that exceeds its `timeout_seconds` is treated as a fail-closed failure (same
  routing), verified by a test with a deliberately slow stub.
- An LLM module whose provider breaker is open short-circuits without calling the provider and
  emits `breaker_tripped`; after `recovery_seconds` it transitions HALF_OPEN and retries
  (reuse `packages/llm_client/circuit_breaker.py` semantics; assert via its existing
  states).
- Default-on for all agent modules through `AgentRuntime`; per-family adapters cover renderer,
  quality, and gate call sites.
- No silent degradation anywhere: every failure path emits an observability event and takes a
  declared closed action.
- Node exporter subprocess isolation is untouched and documented as pre-existing.

## References

- ADR: `docs/adr/033-specialized-module-standard.md` §Decision.5
- `packages/llm_client/circuit_breaker.py:13-108`
- `packages/agents/healing/circuit_breaker.py`, `packages/agents/healing/orchestrator.py`
- `packages/agents/runtime.py:34-45, 152-196`
- `packages/agents/events.py:23-41, 71-73`
- MOD-01 point 4 (observability) + point 5 (fail-closed default)

## Implementation notes

- Production-ready, not a patch: one boundary, applied everywhere, replacing ad-hoc try/except
  in individual nodes. Audit `content_creator/nodes.py:100-127` (per-artifact try/except that
  currently re-raises `ValueError`) and route it through the boundary so a single artifact
  failure becomes a dependency-skip, not a whole-run failure, where policy allows.
- Reuse the existing circuit breakers — do NOT add a third implementation. Pick
  `packages/llm_client/circuit_breaker.py` as the LLM-facing entry (it already delegates to the
  healing breaker and honors a shared store).
- Timeout via `anyio.fail_after` / `move_on_after` (anyio already a dependency, imported in
  `runtime.py:2`).
- The per-module policy (healing vs. skip vs. block) is declared data, not branching logic
  scattered per node — keep it alongside the module's registry entry so MOD-03 can surface it.
- Guard test: assert no module node imports a bare LLM transport or swallows exceptions outside
  the boundary (mirror the researcher guard-test pattern in the RFCs).
