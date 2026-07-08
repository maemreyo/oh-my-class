---
title: "Migrate direct os.environ readers to pydantic-settings (phased); ban ${VAR} in .env files"
status: ready-for-agent
labels: [governance, config, security]
created: 2026-07-08
priority: p1
epic: llm-governance-hardening
sequence: 6
---

> **Phase 1 + immediate part done (2026-07-08); Phases 2-4 remain.**
>
> Immediate part: `.env.example`'s `REDIS_URL` and `DATABASE_URL` (a second,
> previously-unnoted instance of the same `${VAR}` bug) now use literal values.
> `scripts/check_env_drift.py` extended with a `${` ban (hard fail) — verified
> clean today. While adding this, found and fixed a real gap in that same
> script's `_settings_vars()` parser (see `LGH-03`'s addendum) — it only
> recognized `env_prefix`-based `BaseSettings` classes, silently missing the
> new no-prefix `WebhookConfig`.
>
> Phase 1 done: `services/gateway/auth/config.py` (`JWTConfig`) and
> `services/gateway/webhooks/config.py` (`WebhookConfig`, no shared
> `env_prefix` — `TELEGRAM_`/`ZALO_`/`WEBHOOK_` vars don't share one, so each
> field maps to its own bare uppercased name per pydantic-settings' default
> convention). `jwt_handler.py`, `webhooks/telegram.py`, `webhooks/zalo.py`,
> `routers/webhooks.py` now read through these instead of bare `os.environ`.
> Deliberately **not cached** (unlike `features.py`'s pattern) — an early
> caching attempt broke `monkeypatch.setenv`-based test isolation across the
> existing auth test suite; JWT/webhook checks aren't hot enough to need it.
>
> **Real discovery while testing**: pydantic-settings' `env_file=".env"` reads
> the actual `.env` file directly, independent of `monkeypatch.delenv`/process
> env — this is a genuine behavior *improvement* (exactly fixes "a bare
> process silently sees nothing instead of the real secret"), but it means
> `monkeypatch.delenv` no longer simulates "unset" if the repo's real `.env`
> has a value (it does, for `JWT_SECRET`/`TELEGRAM_WEBHOOK_SECRET`/`ZALO_WEBHOOK_SECRET`)
> — tests must use `monkeypatch.setenv(..., "")` (explicit empty, which
> correctly takes priority over the file) instead. Documented in
> `test_auth_webhook_config.py`'s test docstrings so this doesn't confuse the
> next person touching these tests.
>
> **Phases 2-4 not started** — remaining: `slo_alerting.py`,
> `observability/langfuse_config.py`, `observability/langfuse_client.py`,
> `routers/release_evidence.py` (Phase 2); `healing/circuit_breaker.py`,
> `teaching_pack/healing_runtime.py`, `config/features.py`,
> `teaching_pack/features.py`, `teaching_pack/component_strategy_stage.py`,
> `teaching_pack/component_strategy_rollout.py` (Phase 3);
> `tools/ninerouter_web.py`, `services/gateway/main.py` (Phase 4). Each should
> follow the exact pattern established in Phase 1 (one `config.py` per
> logical group, uncached, tests covering both the "configured" and
> "genuinely unconfigured via empty override" cases).
>
> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 5. User explicitly asked for a production-ready, well-tested, phased migration rather than a narrow patch (see memory `feedback_production_ready_over_patches`) — this issue is scoped accordingly, larger than a typical grill-session follow-up.

## What to build

**Immediate, low-risk part:** `.env.example:104`'s `REDIS_URL=redis://${REDIS_HOST}:${REDIS_PORT}` uses `${VAR}` shell-expansion syntax that only docker-compose expands — a bare Python process reading `.env` directly (via `python-dotenv`/`pydantic-settings`) gets the literal, broken string. This is the exact mechanism behind a bug already hit this session (the Promptfoo subprocess-provider issue). Replace with a literal default value; add a one-line check (regex for `${` in `.env*` files) to prevent recurrence.

**Larger part:** 16 files currently read `os.environ.get(...)`/`os.getenv(...)` directly instead of through a `pydantic-settings` `BaseSettings` subclass:

```
packages/agents/tools/ninerouter_web.py
packages/agents/config/features.py
packages/agents/observability/langfuse_client.py
packages/agents/teaching_pack/component_strategy_stage.py
packages/agents/teaching_pack/healing_runtime.py
packages/agents/teaching_pack/features.py
packages/agents/teaching_pack/component_strategy_rollout.py
packages/agents/healing/circuit_breaker.py
services/gateway/slo_alerting.py
services/gateway/main.py
services/gateway/routers/release_evidence.py
services/gateway/routers/webhooks.py
services/gateway/auth/jwt_handler.py
services/gateway/observability/langfuse_config.py
services/gateway/webhooks/telegram.py
services/gateway/webhooks/zalo.py
```

Migrate all of them to `BaseSettings` subclasses (following the `env_prefix` pattern already established in `packages/llm_client/config.py`/`packages/agents/config/models.py`), in phases so each phase is independently reviewable and testable:

- **Phase 1 (highest sensitivity — do first, most carefully reviewed):** `services/gateway/auth/jwt_handler.py`, `services/gateway/webhooks/telegram.py`, `services/gateway/webhooks/zalo.py`, `services/gateway/routers/webhooks.py`.
- **Phase 2:** `services/gateway/slo_alerting.py`, `services/gateway/observability/langfuse_config.py`, `packages/agents/observability/langfuse_client.py`, `services/gateway/routers/release_evidence.py`.
- **Phase 3:** `packages/agents/healing/circuit_breaker.py`, `packages/agents/teaching_pack/healing_runtime.py`, `packages/agents/config/features.py`, `packages/agents/teaching_pack/features.py`, `packages/agents/teaching_pack/component_strategy_stage.py`, `packages/agents/teaching_pack/component_strategy_rollout.py`.
- **Phase 4:** `packages/agents/tools/ninerouter_web.py`, `services/gateway/main.py`.

## Acceptance criteria

- [x] `.env.example`'s `REDIS_URL` (and `DATABASE_URL`, found along the way) use literal values; `scripts/check_env_drift.py` now hard-fails on `${` in `.env.example`.
- [x] Phase 1 lands as its own reviewable change: `JWTConfig`/`WebhookConfig` `BaseSettings` classes, same env var names/defaults as before (verified via `test_auth_webhook_config.py` — 5 tests covering process-env override, defaults, and the real `.env`-file-read behavior).
- [x] Phase 1 (security-sensitive) gets extra test coverage: `test_jwt_secret_missing_fails_loudly`, `test_webhook_config_secrets_default_to_none_not_silent_fallback` — both confirm fail-closed behavior is unchanged.
- [ ] Phases 2-4 not started — zero `os.environ.get`/`os.getenv` calls remaining is not yet true (12 files still pending: `slo_alerting.py`, `observability/langfuse_config.py`, `observability/langfuse_client.py`, `routers/release_evidence.py`, `healing/circuit_breaker.py`, `teaching_pack/healing_runtime.py`, `config/features.py`, `teaching_pack/features.py`, `teaching_pack/component_strategy_stage.py`, `teaching_pack/component_strategy_rollout.py`, `tools/ninerouter_web.py`, `services/gateway/main.py`). Re-open/continue this issue for those phases, following the Phase 1 pattern established here.
- [x] Phase 1 does not change runtime defaults/behavior — confirmed via full `packages/agents/tests/` (13 known pre-existing failures, unchanged) and `services/gateway/tests/` (715 passed, same 3 known pre-existing failures) sweeps.

## Blocked by

Nothing technically; sequenced by risk (Phase 1 most sensitive, done first and most carefully).
