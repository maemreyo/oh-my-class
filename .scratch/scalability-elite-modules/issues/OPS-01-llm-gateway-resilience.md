# [OPS-01] LLM gateway resilience — provider fallback chain + health-checked 9Router bypass + rate-limit-aware backpressure tied to the per-provider breaker

Status: TODO
Labels: ops, resilience, llm
ADR: 034
Depends on: none

## Context

The LLM path is `application → LLMClient (OpenAI SDK, base_url = LLM_ (:20228 default)) → LiteLLM proxy → 9Router (:20128 inside compose) → providers`. This is the single most likely thing to take the whole platform down at the mid-scale target (~5,000 packs/day), so per ADR-034 §1 the LLM gateway is an **availability invariant, not a cost decision** — we spend to stay up.

Two verified gaps close here:

1. **`f.pro` has no fallback.** `infra/litellm/config.yaml` declares `fallbacks: [{f.light: [f.pro]}]` and comments `# f.pro has no fallback — if it fails, healing_node handles escalation`. But "healing_node escalates" means the *run fails to a human*, not that it recovers — so any `f.pro` provider outage becomes run failures, blowing the 99.5% success SLO. ADR-005 flagged this same "9Router-down has no fallback" gap. `f.pro` is the workhorse tier (content_generation, llm_judge, fact_verification, blueprint_design per `packages/agents/config/models.py:38-44`), so this is the dominant availability risk.
2. **9Router is a hard single point.** LiteLLM's only upstream is `api_base: http://9router:20128/v1` for both `f.light` and `f.pro`. If 9Router is degraded (not fully down — slow, partial, returning 5xx), there is no health-checked bypass to a second execution path.

Existing strong mechanics we build additively on (do NOT rebuild):
- **Per-provider circuit breaker** already exists: `CircuitBreaker.provider(...)` at `packages/agents/healing/circuit_breaker.py:114-129`, scope `BreakerScope("provider", provider)`, `coordinates_with_litellm=True`, Redis-backed via `_default_store()` (:215, reads `REDIS_URL`). It emits a `breaker_tripped` observability event on open (`_emit_trip` :201-212). ADR-027 fixed breaker scope to per-provider + per-run in Redis.
- **LiteLLM already has provider-level retry/cooldown**: `router_settings.allowed_fails: 3`, `cooldown_time: 30`, `retry_policy` (RateLimit=3, Timeout=2), Redis-coordinated cooldown (`redis_host/port/password`). This is the infra-error layer (FB3) and must stay the first line — do not duplicate it in Python.
- **Backpressure** at `services/gateway/backpressure.py` gates *run creation* (per-teacher active=3/queued=5, global active=20/queued=50, `queue_delay_seconds=30`) by returning `queued`/`eligible_at`, which the durable queue honors via `claim_next` (`eligible_at <= now`).

The design principle: **LiteLLM owns provider-error handling and cooldown; the Python breaker owns cross-request state and observability; backpressure owns admission.** OPS-01 wires a real fallback chain into LiteLLM, adds a health-checked second execution path, and makes admission (backpressure) react when the provider breaker is open — instead of admitting runs that will immediately fail.

## Scope

- [ ] **Provider fallback chain in LiteLLM** — extend `infra/litellm/config.yaml` `model_list` so `f.pro` and `f.light` are each backed by ≥2 physical deployments (same logical `model_name`, different `litellm_params`/`api_base`), and set `fallbacks` so `f.pro` degrades to an alternate `f.pro` deployment before any run failure. Keep 9Router as primary. Since cost is not a constraint, the fallback may be a more expensive equivalent-quality deployment. Remove the "f.pro has no fallback" comment once real.
- [ ] **Health-checked 9Router bypass** — add a second execution `api_base` for the `f.*` models pointing at an alternate path (direct-to-provider or a second 9Router), wired as a LiteLLM fallback so LiteLLM's `enable_pre_call_checks` + `cooldown_time` route around a degraded 9Router automatically. Build on `infra/litellm/scripts/health-check.sh` for the liveness signal; document the bypass topology in `infra/litellm/README` (or `.env.example`). Closes the ADR-005 gap.
- [ ] **Per-provider breaker → backpressure coupling** — when a provider breaker is `open`/`exhausted` (`CircuitBreaker.provider(name).is_open()` / `.exhausted`), make run *admission* fail-closed: `check_backpressure` (or a thin wrapper it calls) must return `queued` with an `eligible_at` derived from the breaker `recovery_timeout` (not the flat 30s) so new runs are held, not admitted-then-failed. Read breaker state from the shared Redis store; do not admit against a dead provider. This is the "rate-limit-aware backpressure tied to the per-provider circuit breaker" from ADR-034 §1.
- [ ] **Rate-limit awareness** — treat LiteLLM `RateLimitError` (429 from provider) as a breaker-recordable + backpressure signal, not just a per-request retry. When the provider breaker trips on rate limits, admission backs off (previous bullet) rather than continuing to feed the queue. LiteLLM's `RateLimitErrorRetries: 3` stays as the fast in-request retry.
- [ ] **Alert on breaker trips** — a `breaker_tripped` event (already emitted by `_emit_trip`) for a `provider`-scope breaker must raise an **ops page** (wired in OPS-04). For OPS-01, ensure the event carries enough context (`scope`, `breaker_key`, `failures`, `coordinates_with_litellm`) — it already does — and that provider-scope trips are persisted to `run_events` so OPS-03/04 can alert. Do NOT route provider breaker trips to the teacher escalation channel.
- [ ] **Env mapping** — dev: single 9Router upstream, breaker uses in-memory/Null store, no bypass required (LiteLLM optional). staging/prod: full fallback chain + bypass + Redis breaker store + breaker→backpressure coupling active. Gate the coupling on `OMC_ENVIRONMENT in (staging, production)`.
- [ ] **Fail-closed on ambiguity** — if breaker state cannot be read (Redis unreachable) during admission in staging/prod, prefer to *queue* (delay) rather than admit blindly; but never hard-fail the whole gateway on a transient Redis read (breaker `_load_state` already swallows `ConnectionError/OSError` → treats as closed; decide and document the admission-side policy explicitly).

## Acceptance

- Killing the primary `f.pro` deployment (or 9Router) in a staging soak does **not** produce run failures for in-flight or newly-admitted runs: LiteLLM fails over to the alternate `f.pro`/bypass path; measured run-success stays ≥ 99.5% across the outage window.
- With a provider breaker forced `open`, new run-creation requests are **queued with `eligible_at ≈ now + recovery_timeout`**, not admitted; existing queued jobs are not claimed against the dead provider until the breaker half-opens. Verified against a real Postgres queue + real Redis breaker store (no mocks, per repo testing standard).
- A `provider`-scope `breaker_tripped` event lands in `run_events` and triggers an ops page (OPS-04), distinct from any teacher notification.
- Dev still runs with a single upstream and no bypass; nothing in the dev path requires the fallback deployments to exist.
- p95 pack < 8 min is not regressed by the added admission checks (breaker read is a single Redis GET on the create path).

## References

- `infra/litellm/config.yaml` — `model_list` (f.light/f.pro both → `http://9router:20128/v1`), `router_settings.fallbacks` (`f.pro` has none — the gap), `allowed_fails: 3`, `cooldown_time: 30`, `retry_policy`, Redis coordination.
- `infra/litellm/scripts/health-check.sh`, `infra/litellm/.env.example`, `infra/litellm/scripts/create-keys.sh`
- `packages/agents/healing/circuit_breaker.py` — `CircuitBreaker.provider` :114, `.is_open()` :144, `.exhausted` :140, `record_failure` :163, `_emit_trip` :201, `_default_store()` :215 (REDIS_URL).
- `packages/agents/healing/redis_breaker_store.py` — `RedisBreakerStore.from_url` :26, `get` :30 (shared state read for admission).
- `services/gateway/backpressure.py` — `check_backpressure` :60, `BackpressureConfig` :35 (`queue_delay_seconds=30`), `BackpressureResult` (`queued`, `eligible_at`) :46.
- `packages/agents/config/models.py` — `LLMConfig.base_url` :18 (`http://localhost:20228/v1`), tier table :24-44.
- `packages/agents/llm/transport.py` — `complete_non_streaming_chat` :27, `RuntimeError` on empty choices :52.
- `packages/agents/events.py` — `breaker_tripped` in `ObservabilityEventType` :40, `emit_run_event` :71.
- ADR-005 (`docs/adr/005-generic-gate-resume-api.md`) — origin of the 9Router-no-fallback flag; ADR-027 (`docs/adr/027-circuit-breaker-scope.md`) — per-provider Redis breaker scope; ADR-034 §1.

## Implementation notes

- **Keep the two layers separate.** LiteLLM (`num_retries`, `fallbacks`, `cooldown_time`) is the in-request infra-error line; the Python `CircuitBreaker.provider` is the *cross-request* memory that admission and alerting read. Do not reimplement LiteLLM's cooldown in Python, and do not make LiteLLM aware of run admission.
- The breaker→admission coupling is the genuinely new code. Put it in a small, testable pure function (e.g. `provider_admission_delay(breaker_state, now) -> eligible_at | None`) that `check_backpressure` consults, so it can be unit-tested against fabricated breaker states and integration-tested against a real Redis store.
- `_default_store()` reads `REDIS_URL`; the compose Redis is `redis://:${REDIS_AUTH}@redis:6379` (`infra/compose/docker-compose.yml:45`). Ensure the gateway process and the breaker share the same Redis instance the LiteLLM router uses for cooldown, so signals are consistent.
- Fallback deployments must be **equivalent quality** for `f.pro` (it feeds llm_judge/fact_verification/quality_gate) — a weaker fallback would silently degrade quality gates. Document the chosen fallback model and verify it against the golden set (QA-01) before enabling in prod.
- Live-path proof (ADR-032 discipline): the soak test must exercise the real LiteLLM proxy + real breaker, and assert the fallback actually fired (LiteLLM logs `json_logs: true`) — not just that the request eventually succeeded.
