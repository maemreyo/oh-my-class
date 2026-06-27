# ADR-011: Operational Hardening

## Status

**Decided** (2026-06-27) — Pipeline V2 includes idempotency, leases, cancellation, stuck-run recovery, budgets, notifications, and safe admin recovery as first-class production features.

## Context

Pipeline V2 runs long-lived background jobs with teacher gates, live 9Router calls, search/fetch, rendering, healing, and persisted status. Without operational hardening, production will suffer duplicate resumes, stuck jobs, stale gates, runaway retries, unclear cancellation, and manual DB recovery.

## Decision

Pipeline V2 must implement operational hardening from the start.

Idempotency:

- `POST /run`, `POST /run/{run_id}/resume`, cancel, retry, and admin recovery actions require idempotency handling.
- Persist idempotency records with actor, endpoint/action, request hash, response summary, status, and expiry.
- Repeated requests with the same key and same body return the original result.
- Same key with a different body is rejected.

Concurrency:

- Gate resume requires current `gate_interrupt_id` and expected gate version.
- Resume uses atomic compare-and-set from awaiting state to resuming state.
- Stale resume returns `409` with current gate/status.

Jobs and leases:

- Use an explicit Postgres `run_jobs` table.
- Jobs have status, lease owner, lease expiry, attempts, heartbeat, and recovery metadata.
- Workers renew leases and recovery sweeper reclaims expired leases.

Cancellation and stuck recovery:

- Add first-class run cancellation.
- Gates never auto-approve on timeout; they escalate or notify.
- RunContract defines max run, stage, artifact attempt, and gate durations.
- A recovery sweeper detects expired leases, stuck runs, and gate timeouts.

Budgets and limits:

- Budgets are reliability controls, not only cost controls.
- RunContract includes limits for duration, LLM calls, attempts, healing, search queries, fetches, prompt size, output tokens, artifact parallelism, and live 9Router concurrency.
- Tenant/user limits cap active and queued runs.
- Budget exceedance policy can hard-fail, degrade, or ask human depending on risk.

Notifications:

- V2 has a first-class notification model with in-app notifications now and external channel interfaces later.
- Notification delivery records are idempotent.

Admin recovery:

- Provide minimal admin/recovery APIs for safe actions only: retry stuck job, retry failed artifact, retry notification, cancel run, re-open current gate, mark escalated.
- Arbitrary stage jumps or direct state mutation are not allowed.

## Consequences

- Production behavior is recoverable and auditable.
- Double-clicks, retries, stale gates, and worker crashes have defined outcomes.
- Queue pressure is visible to the UI.
- Admin support does not require manual database edits.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| Rely on app-level guards | Faster | Duplicate jobs/resumes and stuck runs are likely |
| External queue only | Mature semantics | More infrastructure; less transparent DB recovery |
| Explicit Postgres jobs + idempotency | Inspectable and testable | More schema and edge-case tests |
| Gates auto-approve on timeout | Less blocking | Violates human approval invariants |
