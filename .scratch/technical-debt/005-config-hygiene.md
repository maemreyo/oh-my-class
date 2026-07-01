---
title: Config hygiene — LLM endpoint port and model alias
status: done
labels: []
created: 2026-06-30
---

## What to build

Resolve config drift between code defaults and the real environment.

- **Port mismatch**: code default and `.env.example` now agree on `LLM_BASE_URL=http://localhost:20228/v1`, the operator's actual local 9Router endpoint. No silent divergence.
- **Model alias**: every agent uses `4omc` — keep (intentional for the single-operator setup) but confirm per-task override via `MODEL_*` env still works and is documented.
- Document the LLM topology (host-9Router `:20228`, optional LiteLLM in prod) in one place.

## Acceptance criteria

- [x] Code default and `.env`/`.env.example` agree on the LLM endpoint port (`:20228`), or a single source of truth is documented with no conflicting literals.
- [x] Per-task model override via env is verified and documented; `4omc` default retained.
- [x] LLM topology is documented (host-9Router + optional prod LiteLLM).

## Detailed test suite

- [x] `packages/llm_client/tests/test_client.py` and `packages/agents/config/tests/test_gate_config.py`: the resolved `LLM_BASE_URL` matches the documented default; `.env.example` and code default do not conflict.
- [x] `packages/agents/config/tests/test_gate_config.py::TestModelConfig::test_env_override_model`: setting a `MODEL_*` env var overrides the `4omc` default for that task.
- [x] Run `uv run pytest packages/llm_client/tests/test_client.py packages/agents/config/tests/test_gate_config.py::TestModelConfig -q --disable-warnings`.

## Blocked by

None - can start immediately
