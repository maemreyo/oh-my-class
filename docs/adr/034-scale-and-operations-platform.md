# ADR-034: Scale & Operations Platform

## Status

**Proposed** (2026-07-03) — Consolidated platform decisions to run at the mid-scale target and
operate/verify it. Detail lives in the issue set (OPS-*, SCALE-*, SEC-*). The scale *mechanics*
are already strong (durable leased job queue with `SKIP LOCKED`, env-mapped
checkpointer/store to Postgres, backpressure, per-run budget) — this ADR closes the operational,
storage, tenancy, resilience, and safety gaps around them.

## Target (north star)

Mid-scale SaaS: ~1,000 active teachers, ~5,000 packs/day peak, **p95 pack < 8 min**, **99.5%
run-success**. Cost is not a constraint. These are the acceptance bars for every OPS/SCALE issue.

## Decision

1. **LLM gateway = availability invariant** (not cost): LiteLLM provider fallback chain +
   health-checked 9Router bypass (closes ADR-005 gap); rate-limit-aware backpressure tied to the
   per-provider circuit breaker; alert on breaker trips. Model routing stays config-per-agent +
   a per-stage **latency budget** to hold p95.
2. **Observability = ops backbone**: Langfuse for per-run tracing; a thin `run_events` KPI
   dashboard (success rate, p95 per stage, queue depth, escalate/day, healing distribution,
   fast-lane rate, breaker trips, tokens/run). SLOs are monitored objects with error budgets +
   **tiered alerts** (page: success<99.5%, breaker open, DLQ growth, queue not draining; warn:
   p95>8min, queue growth, escalate spike). Ops alerts separate from teacher escalate notices.
3. **Storage**: exports move from local `.scratch` to **object storage (S3/MinIO)** behind the
   existing `TeachingPackExportWriter` Protocol, env-mapped (dev=fs, staging/prod=object); serve
   via signed URLs; store keys in DB, not paths.
4. **Worker fleet**: dedicated worker deployable (`WORKER_MODE != in_process`), **autoscaled on
   queue depth**, ceilinged by provider rate limits; in-process kept for dev.
5. **Data lifecycle**: retention/TTL with **revision-window-aware pruning** (never prune
   pending/escalated/within-revision-window), `run_events` time-partitioned + KPI rollup before
   prune, object-storage lifecycle rules; scheduled cleanup (model on the recovery sweeper).
6. **Multi-tenancy**: additive **org/school layer** (`org_id`) with org-scoped quotas + query
   scoping; row-scoping/RLS, not physical isolation.
7. **Resilience**: formalize side-effect **idempotency/exactly-once** (export keys, event
   dedup, checkpoint-resume) + lease-flap resilience test; bounded retry → **dead-letter** +
   page + replay (infra-poison ≠ quality-escalate).
8. **Zero-downtime deploys**: worker drain on SIGTERM, expand-contract Alembic migrations,
   feature flags for staged rollout/rollback.
9. **Config/secrets**: one validated `pydantic-settings` model, boot-time fail-fast, secret
   manager in staging/prod, reject dev defaults (`changeme`), no secrets in logs.
10. **K-12 data privacy (privacy-by-design)**: minimize/pseudonymize `student_evidence` (never
    logged/traced/over-persisted), encryption at rest + in transit, retention + right-to-delete
    (per teacher/org), data-access audit (extend `teacher_audit_log`), FERPA/COPPA/Vietnam
    Decree-13 mapping documented.
11. **Completeness**: API rate-limiting/abuse limits; quality-drift eval harness (golden set +
    Cohen's kappa, `calibrate_judge.py`); load/perf test proving the SLOs; DR backup-restore
    runbook; data backfill migrations (org_id, object storage); teacher-dashboard WCAG.

## Consequences

- The mid-scale SLOs become operable + verifiable; storage/tenancy/deploy no longer single-node.
- Larger surface, but each item is additive on strong existing mechanics — not a rewrite.

## Alternatives Considered

| Option | Pros | Cons |
|---|---|---|
| Consolidated platform ADR + detailed issues (chosen) | Few ADRs, depth in tickets (per request) | One broad ADR to keep current |
| One ADR per concern (10+) | Fine-grained | Too many ADRs — against the "ít ADR" request |
| Defer scale work until it hurts | Less work now | Retrofitting storage/tenancy/privacy is far costlier later |
