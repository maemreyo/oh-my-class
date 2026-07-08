---
title: "Config-drift lint: every env var used in code must appear in .env.example, and vice versa"
status: ready-for-agent
labels: [governance, config, ci]
created: 2026-07-08
priority: p2
epic: llm-governance-hardening
sequence: 3
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 2. Scope note: `ModelAssignments`/`MaxTokensConfig`/`NinerouterConfig` (`packages/agents/config/models.py`) are confirmed **not** duplicative — each owns a distinct `env_prefix` for a distinct concept. This issue is about catching drift (a var used in code but missing from `.env.example`, or vice versa), not about consolidating settings classes.

## What to build

`scripts/check_env_drift.py`:
1. Collect every env var name referenced in `packages/`/`services/` via `os.environ.get(...)`, `os.getenv(...)`, and every `env_prefix="X_"` + its `BaseSettings` field names (reconstruct the full var name, e.g. `env_prefix="MAX_TOKENS_"` + field `content_creator` → `MAX_TOKENS_CONTENT_CREATOR`).
2. Collect every var name defined in `.env.example`.
3. Report (fail CI) on any var in (1) not in (2) — code references a setting nobody documented — and, separately, flag (warn, don't fail — some `.env.example` entries may be intentionally aspirational/commented) vars in (2) not in (1).

## Acceptance criteria

- [ ] Script correctly reconstructs prefixed var names from `BaseSettings` subclasses (not just bare `os.environ` calls).
- [ ] Script passes cleanly against current `.env.example` and codebase (fix any real drift it finds as part of landing this).
- [ ] Added to CI as a blocking check for the "used in code but undocumented" direction.

## Blocked by

Nothing.
