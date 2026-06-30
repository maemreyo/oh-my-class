---
title: Chaos/fault injection for healing + production-trace feedback loop
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Test the system's recovery behavior under fault, and close the loop from production failures back into the test suite.

- **Chaos/fault injection**: inject faults at seams — LLM transient errors (provider exhaustion → requeue per scaling-resilience 003), schema failures, render subprocess crashes, gate timeouts — and assert the healing path (runtime-parity 002: retry → rewrite → reroute → replan → escalate) behaves correctly and escalates fail-closed on exhaustion.
- **Production-trace feedback**: a mechanism to capture failing production traces (from Langfuse) and turn them into regression test cases (golden additions or targeted reproductions).
- Fault injection is deterministic where possible (inject at the transport/adapter boundary); healing-quality assertions use real LLM.

## Acceptance criteria

- [ ] Fault injection at LLM/schema/render/gate seams exercises each healing strategy and the fail-closed escalation.
- [ ] Provider-exhaustion faults route to requeue (not FAILED) per scaling-resilience 003; permanent faults fail closed.
- [ ] A render crash is fail-closed (no empty pack); a gate timeout auto-escalates per its TTL.
- [ ] A documented workflow captures a failing Langfuse trace and materializes it as a regression test (golden add or reproduction).
- [ ] Chaos tests are tiered (deterministic injection in fast tier; healing-quality assertions in `real_llm`).

## Detailed test suite

(Real DB; deterministic fault injection; real LLM for healing-quality.)

- [ ] `tests/chaos/test_healing_strategies.py`: each injected fault triggers the expected healing strategy; exhaustion escalates fail-closed.
- [ ] `tests/chaos/test_provider_exhaustion.py`: a transient-exhaustion fault requeues with backoff; a permanent fault FAILs.
- [ ] `tests/chaos/test_render_and_gate_faults.py`: render crash is fail-closed; gate timeout auto-escalates.
- [ ] `tests/feedback/test_trace_to_testcase.py`: a captured failing trace is converted into a runnable regression case.
- [ ] Run `uv run pytest tests/chaos tests/feedback -v` (deterministic) and the `real_llm`-marked healing-quality subset nightly.

## Blocked by

- .scratch/testing/001-harness-and-tiering-foundation.md
- .scratch/runtime-parity/002-healing-orchestrator-stage-recovery.md
- .scratch/scaling-resilience/003-provider-and-budget-resilience.md
