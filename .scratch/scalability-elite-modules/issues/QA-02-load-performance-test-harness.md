# [QA-02] Load / performance test harness

Status: TODO
Labels: quality, ops
ADR: 034
Depends on: OPS-06

## Context

The north-star SLOs — **~5,000 packs/day peak, p95 pack < 8 min, 99.5% run-success** — are the
acceptance bar for the entire ADR-034 workstream, yet nothing **drives the pipeline at target
concurrency to prove them**. The scale mechanics exist (durable leased queue, backpressure,
per-run budget, checkpointer, and the OPS-06 dedicated worker fleet + autoscaling), and OPS-03/04
provide the dashboards + SLOs to *observe* production. But an SLO that has never been driven under
representative load is **unvalidated** — we would first learn the system's real p95 and success
rate in production, which is unacceptable at this scale.

This harness closes that: a repeatable load test that pushes realistic traffic through the real
pipeline, measures the SLO metrics, and produces a perf report — run pre-release so regressions in
throughput/latency are caught before ship.

## Scope

- [ ] **Load driver**: a harness that submits realistic run requests (mix of generate +
      diagnose_then_generate, representative `raw_request`/`class_info` sizes, spread across many
      teachers/orgs) at a configurable rate, up to and beyond the **5,000 packs/day peak**
      (including a burst profile, not just steady state).
- [ ] **Run against the real fleet**: exercise the OPS-06 worker fleet
      (`WORKER_MODE != in_process`) with autoscaling on queue depth, real DB, real object storage,
      and a real (or realistic gateway to the) LLM path — the SLOs are about the live system.
- [ ] **Measure the SLO metrics**: p95 (and p50/p99) pack latency, run-success rate, queue depth
      over time, per-stage latency, breaker trips, tokens/run — reusing the OPS-03 `run_events`
      KPI signals so the harness and dashboard measure the same thing.
- [ ] **Assert the SLOs**: the harness passes only if p95 < 8 min AND success ≥ 99.5% AND the
      queue drains (no unbounded growth) at the target rate. Fail with a clear breakdown otherwise.
- [ ] **Perf report**: emit a written report (throughput achieved, latency percentiles, success
      rate, queue behavior, autoscaling behavior, breaker trips, cost/tokens) suitable for
      release sign-off and trend comparison across releases.
- [ ] **Pre-release wiring**: run in the pre-release path (coordinate with VER-04
      merge-vs-release contract) so a change that regresses throughput/latency below the SLOs
      blocks release. Support a lighter smoke profile for fast CI and the full profile at release.
- [ ] **Baseline + regression**: store a baseline perf profile and flag regressions vs it.

## Acceptance

- The harness drives the pipeline at the **5,000 packs/day peak** (and a burst) through the real
  worker fleet and produces a perf report with p95/p99 latency, success rate, and queue behavior.
- The harness **asserts** p95 < 8 min, success ≥ 99.5%, and a draining queue, and fails clearly
  when any SLO is breached — proven by running it once green and once red (e.g. throttled fleet).
- Autoscaling on queue depth (OPS-06) is observed to engage under load in the report.
- A regression vs the stored baseline is flagged.
- The pre-release profile blocks release on SLO breach; a fast smoke profile exists for CI.

## References

- ADR-034 Target section — the SLOs (5,000/day, p95<8min, 99.5%) this harness must prove.
- OPS-06 (worker fleet + autoscale) — the deployment under test; hard dependency.
- OPS-03 (KPI dashboard) / OPS-04 (SLOs + alerting) — shared metric definitions via `run_events`.
- `services/gateway/backpressure.py`, `services/gateway/budget.py` — limits the load must respect.
- VER-04 (merge-vs-release contract) — release-gate wiring.
- ADR-034 decision 11.

## Implementation notes

- Reuse the OPS-03 `run_events`-derived metrics as the source of truth so "measured" == "what the
  dashboard shows" — don't invent a parallel measurement path.
- Realistic input mix matters: diagnose_then_generate is heavier than plain generate; skewing the
  mix would make the p95 number meaningless.
- The red-path proof (deliberately under-provisioned fleet) is what proves the harness actually
  *catches* an SLO breach, not just reports numbers.
- Cost is not a constraint (north star) — provision the fleet to hit the SLOs; the harness's job
  is to prove the SLOs are met at that provisioning, and to reveal where they aren't.
