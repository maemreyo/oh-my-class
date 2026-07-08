---
title: "Config-drift lint: every env var used in code must appear in .env.example, and vice versa"
status: done
labels: [governance, config, ci]
created: 2026-07-08
priority: p2
epic: llm-governance-hardening
sequence: 3
---

> Addendum (2026-07-08, during LGH-06 Phase 1): found and fixed a real gap this
> script's own `_settings_vars()` had — it only recognized `BaseSettings`
> subclasses that declare `env_prefix=...`; classes with no prefix (valid
> pydantic-settings usage — each field maps to its own bare uppercased name,
> used by the new `services/gateway/webhooks/config.py`'s `WebhookConfig`,
> which covers `TELEGRAM_WEBHOOK_SECRET`/`WEBHOOK_*`/`ZALO_WEBHOOK_SECRET` —
> vars that don't share a common prefix) were silently skipped, so their vars
> briefly regressed to false "WARN: not referenced in code" after the LGH-06
> migration landed. Fixed to handle both cases; added a selftest regression
> case (`no_prefix_sample`) so this doesn't silently break again.

> Done (2026-07-08): Built `scripts/check_env_drift.py` (regex + light AST-free
> parsing, no config/plugin system). It found real drift: `LLM_TIMEOUT` in
> `.env.example` didn't match the actual `LLMClientConfig` field `timeout_s`
> (renamed to `LLM_TIMEOUT_S`), and ~60 vars referenced in code (all of
> `TokenBudgetConfig`'s `BUDGET_*` fields, most of `GateConfig`'s `GATE_*`
> fields, all of `TeachingPackConfig`'s `TEACHING_PACK_*` fields, plus
> assorted bare `os.getenv`/`os.environ.get` flags — `FEATURE_*`, `OMC_*`,
> `WORKER_*`, `WEBHOOK_*`, `NINEROUTER_BASE_URL`/`NINEROUTER_API_KEY`,
> `LLM_TEMPERATURE`, `LANGFUSE_HOST`) were missing from `.env.example` and
> have been added with their code defaults. Script now passes with exit 0;
> wired into CI's `test-python` job as a blocking step. The remaining
> `.env.example`-only vars (POSTGRES_*, REDIS_*, GATEWAY_*, provider keys,
> `MODEL_LEAD_AGENT`) are correctly flagged as warn-only — they're
> docker-compose/dashboard-only, not read via `os.environ`/`BaseSettings` in
> Python code.

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 2. Scope note: `ModelAssignments`/`MaxTokensConfig`/`NinerouterConfig` (`packages/agents/config/models.py`) are confirmed **not** duplicative — each owns a distinct `env_prefix` for a distinct concept. This issue is about catching drift (a var used in code but missing from `.env.example`, or vice versa), not about consolidating settings classes.

## What to build

`scripts/check_env_drift.py`:
1. Collect every env var name referenced in `packages/`/`services/` via `os.environ.get(...)`, `os.getenv(...)`, and every `env_prefix="X_"` + its `BaseSettings` field names (reconstruct the full var name, e.g. `env_prefix="MAX_TOKENS_"` + field `content_creator` → `MAX_TOKENS_CONTENT_CREATOR`).
2. Collect every var name defined in `.env.example`.
3. Report (fail CI) on any var in (1) not in (2) — code references a setting nobody documented — and, separately, flag (warn, don't fail — some `.env.example` entries may be intentionally aspirational/commented) vars in (2) not in (1).

## Acceptance criteria

- [x] Script correctly reconstructs prefixed var names from `BaseSettings` subclasses (not just bare `os.environ` calls).
- [x] Script passes cleanly against current `.env.example` and codebase (fix any real drift it finds as part of landing this).
- [x] Added to CI as a blocking check for the "used in code but undocumented" direction.

## Blocked by

Nothing.
