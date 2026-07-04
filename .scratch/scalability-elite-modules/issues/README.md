# scalability-elite-modules — issue set

Next-phase plan: take the system from "pilot / basic multi-instance production-ready" to
**world-class scalable + elite specialized modules**. Grilled + specced 2026-07-03 (28 questions).
Local tracking only (NOT on GitHub remote). No code implemented — ADRs + detailed issues only.

North star (acceptance bar for every issue): ~1,000 teachers, ~5,000 packs/day peak,
**p95 pack < 8 min**, **99.5% run-success**. Cost is not a constraint.

Guiding principle: production-ready rebuilds over patches; big-bang + guard tests;
harness / smart / flexible / scalable / high-readability / SoC / modular / standalone /
well-tested / testable / UI-UX-user-centric; well-adapted to existing app features.

## ADRs (concise decision records; depth lives in the issues)

- `docs/adr/032-verification-integrity-and-engineering-discipline.md`
- `docs/adr/033-specialized-module-standard.md`
- `docs/adr/034-scale-and-operations-platform.md`
- New module RFCs: `docs/rfc/differentiation-module.md`, `docs/rfc/standards-alignment-module.md`
  (plus existing `docs/rfc/{researcher-001-upgrade,localization-agent,accessibility-agent}.md`)

## Issue groups

**Verification integrity (ADR-032)** — VER-01 live-path proof CI gate (CodeGraph) · VER-02 test
taxonomy + tiered CI · VER-03 safety adversarial/mutation · VER-04 merge-vs-release contract ·
VER-05 observability live-emitter meta-test.

**Specialized Module Standard (ADR-033)** — MOD-01 standard + 6-point checklist · MOD-02
`make new-module` scaffolder · MOD-03 unified manifest + drift CI · MOD-04 contract versioning +
golden fixtures · MOD-05 per-module fault isolation · MOD-06..10 build the 5 modules
(researcher-upgrade, accessibility, localization, differentiation, standards-alignment).

**Scale & operations (ADR-034)** — OPS-01 LLM resilience · OPS-02 model routing + latency budget ·
OPS-03 KPI dashboard · OPS-04 SLO + alerting · OPS-05 object-storage exports · OPS-06 worker fleet
+ autoscale · OPS-07 data lifecycle/retention · OPS-08 zero-downtime deploys · OPS-09
multi-tenancy (org layer) · OPS-10 idempotency/exactly-once · OPS-11 poison-run DLQ · OPS-12
config/secrets · OPS-13 DR backup-restore · OPS-14 data backfill migrations.

**Safety / privacy / quality (ADR-034)** — PRIV-01 K-12 data privacy (FERPA/COPPA/Decree-13) ·
SEC-01 API rate limiting/abuse · QA-01 quality-drift eval harness · QA-02 load/perf test (prove
SLOs) · QA-03 teacher-dashboard WCAG.

## Suggested execution order

1. **Foundation & discipline first:** VER-01..05 (so everything after is verified live-path),
   MOD-01..05 (the standard the modules build on).
2. **Scale backbone:** OPS-05 (object storage), OPS-06 (worker fleet), OPS-01 (LLM resilience),
   OPS-03/04 (observability + SLO), OPS-12 (config/secrets).
3. **Correctness at scale:** OPS-10 (idempotency), OPS-11 (DLQ), OPS-07 (lifecycle), OPS-08
   (zero-downtime), OPS-09 (tenancy), OPS-13/14 (DR + backfill).
4. **Safety/quality gates:** PRIV-01, SEC-01, VER-03, QA-01.
5. **Elite modules:** MOD-06..10 (on the finished standard + AgentRuntime).
6. **Prove it:** QA-02 load test vs the SLOs; QA-03 dashboard WCAG.
