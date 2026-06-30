---
title: Config hygiene — LLM endpoint port and model alias
status: ready-for-agent
labels: [ready-for-agent]
created: 2026-06-30
---

## What to build

Resolve config drift between code defaults and the real environment.

- **Port mismatch**: code default `LLM_BASE_URL=http://localhost:20128/v1` (`config.py`) vs `.env` `:20228` (the operator's actual local 9Router). Standardize the default to **`:20228`** (the real endpoint) or make the code default read from a single documented source; ensure `.env.example` matches. No silent divergence.
- **Model alias**: every agent uses `4omc` — keep (intentional for the single-operator setup) but confirm per-task override via `MODEL_*` env still works and is documented.
- Document the LLM topology (host-9Router `:20228`, optional LiteLLM in prod) in one place.

## Acceptance criteria

- [ ] Code default and `.env`/`.env.example` agree on the LLM endpoint port (`:20228`), or a single source of truth is documented with no conflicting literals.
- [ ] Per-task model override via env is verified and documented; `4omc` default retained.
- [ ] LLM topology is documented (host-9Router + optional prod LiteLLM).

## Detailed test suite

- [ ] `tests/test_config_endpoint.py`: the resolved `LLM_BASE_URL` matches the documented default; `.env.example` and code default do not conflict.
- [ ] `tests/test_model_override.py`: setting a `MODEL_*` env var overrides the `4omc` default for that task.
- [ ] Run `uv run pytest tests/test_config_endpoint.py tests/test_model_override.py -v`.

## Blocked by

None - can start immediately
