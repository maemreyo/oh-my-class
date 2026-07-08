---
title: "Migrate direct os.environ readers to pydantic-settings (phased); ban ${VAR} in .env files"
status: ready-for-agent
labels: [governance, config, security]
created: 2026-07-08
priority: p1
epic: llm-governance-hardening
sequence: 6
---

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

- [ ] `.env.example`'s `REDIS_URL` uses a literal value; a lint/check bans `${` in `.env*` files going forward.
- [ ] Each phase lands as its own reviewable change: new `BaseSettings` subclass(es) with the same env var names/defaults as today (no behavior change to defaults), a test proving the settings class loads correctly both from `.env` and from real process env vars (covering exactly the load-order gap that caused the original `REDIS_URL` bug — a bare Python process vs. a process that inherited env from docker-compose/the gateway's own startup).
- [ ] Security-sensitive modules (Phase 1) get extra test coverage: confirm secrets still fail loudly (not silently default) when missing, matching current behavior.
- [ ] After all 4 phases, zero `os.environ.get`/`os.getenv` calls remain in `packages/`/`services/` outside `pydantic-settings` class definitions themselves (grep-verify as the phase-4 acceptance check).
- [ ] Each phase does not change runtime defaults/behavior — this is a loading-mechanism migration, not a config-value change.

## Blocked by

Nothing technically; sequenced by risk (Phase 1 most sensitive, done first and most carefully).
