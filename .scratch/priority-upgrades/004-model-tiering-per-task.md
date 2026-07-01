---
title: Model tiering per task in ModelAssignments
status: done
labels: [llm, cost, model-routing, config]
created: 2026-07-01
---

## What to build

All 15 `ModelAssignments` fields in `packages/agents/config/models.py` default to `"4omc"`. There is no per-task differentiation despite clear cost/quality tiers in the task set:

- **Needs strongest model** (complex reasoning, multi-step, high-stakes): `blueprint_design`, `content_generation`, `llm_judge`, `fact_verification`, `quality_gate`.
- **Medium model** (structured output, moderate complexity): `planner`, `researcher`, `content_creator`, `reviewer`, `content_review_light`.
- **Fast/cheap model** (classification, reformatting, short context): `summarization`, `title_generation`, `schema_rewrite`.

The structure already supports per-agent env override via `MODEL_*` prefix (e.g. `MODEL_BLUEPRINT_DESIGN=gpt-4o`). This issue is to:

1. **Document the tier table** (which task → which tier) as a comment in `models.py` so operators know what to override.
2. **Add default aliases** for two tiers to `.env.example`: `MODEL_FAST_DEFAULT` (for cheap tasks) and `MODEL_STRONG_DEFAULT` (for reasoning-heavy tasks) — the operator sets these once, and the `ModelAssignments` factory reads them as fallback for the appropriate slots.
3. **Update `ModelAssignments`** to wire the tier fallbacks: fast-tier fields fall back to `MODEL_FAST_DEFAULT` then `"4omc"`; strong-tier fields fall back to `MODEL_STRONG_DEFAULT` then `"4omc"`. Per-task env vars (`MODEL_*`) still override.

This is **operator-configurable infrastructure**, not a code change that affects a single-model deployment (9Router `4omc` everywhere still works as before — the tiers are opt-in). The goal is to make it easy to point expensive tasks at a stronger model when the operator has access to one.

## Acceptance criteria

- [x] `ModelAssignments` fields are annotated with their tier (`# fast | medium | strong`) in `models.py`.
- [x] `.env.example` adds `MODEL_FAST_DEFAULT` and `MODEL_STRONG_DEFAULT` with comment explaining the tier fallback.
- [x] `ModelAssignments` reads `MODEL_FAST_DEFAULT` / `MODEL_STRONG_DEFAULT` as fallbacks for the appropriate slots; single-model (no env vars set) behavior is unchanged (still `"4omc"` for all).
- [x] `packages/agents/config/tests/test_gate_config.py` covers the tier-fallback logic: set `MODEL_STRONG_DEFAULT=gpt-4o` → `ModelAssignments().llm_judge == "gpt-4o"`.
- [x] Manifest sync: `architecture.manifest.json::models.assignments` reflects the tiered defaults.

## Detailed test suite

(Deterministic — no LLM needed.)

- [x] `packages/agents/config/tests/test_model_tiering.py`: test tier fallback precedence: per-task env > tier-default env > `"4omc"`. Test that setting no env vars yields `"4omc"` for all fields (regression).

## Verification

- 2026-07-01: `uv run pytest packages/agents/config/tests/test_model_tiering.py packages/agents/config/tests/test_gate_config.py -q` → `61 passed`.
- 2026-07-01: LSP diagnostics clean for `packages/agents/config/models.py` and `packages/agents/config/tests/test_model_tiering.py`.

## Blocked by

None — config-only change, no blockers.
