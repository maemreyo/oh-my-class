# [SEC-01] API rate limiting + abuse limits

Status: TODO
Labels: security, ops
ADR: 034
Depends on: none

## Context

The gateway authenticates via `JWTMiddleware`, which gates all non-public paths
(`services/gateway/middleware/auth_middleware.py`), and ownership is enforced per-row
(`get_run_with_ownership`, `services/gateway/routers/teaching_pack_deps.py`; guard test
`test_no_unscoped_accessor_in_routers.py`). Backpressure limits *concurrent runs* per teacher and
globally (`services/gateway/backpressure.py`).

But there is **no per-token or per-IP request rate limiting** on the gateway, and **no
request/input-size limits or abuse throttling**. Authz answers "may this caller touch this row";
it does not answer "is this caller hammering the API" or "is this a 50 MB payload". At the
north-star scale (public-facing SaaS, ~1,000 teachers), an abusive or buggy client can degrade
availability, blow the latency budget, or drive cost even though authz is intact. Backpressure
protects the *run pipeline* but not the *HTTP surface* (cheap-but-frequent endpoints, auth
attempts, oversized inputs).

## Scope

- [ ] **Per-token rate limiting**: limit requests per authenticated principal (from the JWT
      subject) over a sliding/rolling window, applied as middleware after auth
      (`middleware/auth_middleware.py` ordering). Return `429` with `Retry-After`. Tiers may vary
      by role (teacher vs admin) and endpoint class (mutating vs read).
- [ ] **Per-IP rate limiting**: limit requests per client IP (respecting trusted proxy headers)
      including on **unauthenticated** paths (login/token) to blunt credential-stuffing and
      anonymous abuse. Return `429` with `Retry-After`.
- [ ] **Request / input-size limits**: enforce a max request body size and max sizes on
      user-supplied fields that drive cost (`raw_request`, `class_info`/`student_evidence`)
      before they reach the pipeline; reject oversized payloads with `413`. Choose limits that
      comfortably fit legitimate use but bound worst-case.
- [ ] **Abuse throttling**: escalating throttle / temporary block for principals or IPs that
      repeatedly trip limits or fail auth, distinct from steady-state rate limits. Emit a metric
      the OPS-04 alerting can watch.
- [ ] **Shared, horizontal-safe counter store**: implement counters in a store shared across
      gateway instances (Redis is already in the stack) so limits hold across the worker/gateway
      fleet (OPS-06), not per-process.
- [ ] **Observability**: emit rate-limit/abuse events + counts for the OPS-03 dashboard and
      wire an OPS-04 warn/alert on sustained 429 spikes (possible attack or misbehaving client).
- [ ] Explicitly **do not duplicate** authz (already enforced) or run-concurrency backpressure
      (already enforced) — this is the HTTP-surface layer that complements both.

## Acceptance

- Exceeding the per-token limit returns `429` + `Retry-After`; within-limit traffic is unaffected
  — proven by a live-path test.
- Exceeding the per-IP limit on an unauthenticated path returns `429` — proven by a test.
- An oversized body / oversized `raw_request`/`student_evidence` field is rejected with `413`
  before entering the pipeline.
- Limits hold **across two gateway instances** sharing the Redis counter store (not per-process)
  — proven by a multi-instance test.
- Repeated limit trips / auth failures trigger escalating throttle and emit an abuse metric that
  OPS-04 can alert on.

## References

- `services/gateway/middleware/auth_middleware.py` — `JWTMiddleware`, public-path handling,
  middleware ordering (rate-limit middleware sits alongside).
- `services/gateway/routers/teaching_pack_deps.py` — `get_run_with_ownership` (authz, already done).
- `services/gateway/backpressure.py` — run-concurrency limits (complementary, not this).
- `services/gateway/routers/teaching_pack_runs.py:80-90` — create path (input-size checks target
  `raw_request` / `class_info`).
- OPS-06 (worker/gateway fleet — why counters must be shared), OPS-03/04 (metrics + alerting).
- ADR-034 decision 11.

## Implementation notes

- Prefer a well-tested limiter (e.g. `slowapi`/`limits` backed by Redis) over a hand-rolled one;
  the counter store MUST be Redis (already deployed) so limits are fleet-wide.
- Order matters: per-IP + input-size checks should run early (cheap rejection); per-token after
  auth resolves the principal.
- Set size limits against real payloads — inspect typical `raw_request`/`student_evidence` sizes
  before choosing a ceiling so legitimate diagnose-then-generate requests are not blocked.
- Keep `429`/`413` responses secret-free and PII-free (coordinate with PRIV-01).
