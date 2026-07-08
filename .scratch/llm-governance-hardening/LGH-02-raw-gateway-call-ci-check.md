---
title: "Grep-based CI check: ban raw LLM-gateway host/port outside allowlisted probes"
status: done
labels: [governance, ci, llm]
created: 2026-07-08
priority: p3
epic: llm-governance-hardening
sequence: 2
---

> Done (2026-07-08): Added `scripts/check_no_raw_gateway_calls.py` (grep `packages/`+`services/` `*.py`, excluding `tests/`, for the `20228` literal) and wired it into `.github/workflows/ci.yml` as `lint-no-raw-gateway-calls`. Reality had drifted from this issue's "exactly two files" premise: a re-check via the confirm command found the literal in 5 files, not 2. Three are legitimate but weren't anticipated here — `packages/llm_client/config.py` and `client.py` (LLMClient's own default `base_url` and a docstring — that package *is* the sanctioned client, not a bypass of it) and `services/gateway/routers/release_evidence.py` (wires a default into the already-allowlisted `provider_evidence.py`; imports no `httpx` itself). The script exempts `packages/llm_client/` wholesale and allowlists three files (the original two plus `release_evidence.py`). Verified: clean run exits 0 today; a temporary synthetic violation (`packages/agents/_tmp_violation_check.py`, deleted immediately after) was caught with correct file:line output and exit 1. No CONTRIBUTING.md exists in this repo, so the "why" documentation lives in the script's own module docstring instead of a separate doc file.

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 1 follow-up. `import-linter` (see `LGH-01`) cannot distinguish "httpx used to probe the gateway" from "httpx used to bypass LLMClient" — both just import `httpx`, a general-purpose library. This needs a different, narrower mechanism.

## What to build

Currently exactly two files legitimately call the LLM gateway (`:20228`) directly via `httpx`, for health-check/release-evidence purposes rather than agent completions:
- `packages/agents/llm/smoke.py`
- `services/gateway/provider_evidence.py`

Add `scripts/check_no_raw_gateway_calls.py`: grep `packages/` + `services/` (excluding `tests/`) for the gateway host/port literal (`20228`, and `LLMClientConfig.base_url`'s default host if it changes), fail if found outside a hardcoded allowlist of the two files above. Wire it into CI (`.github/workflows/ci.yml`) alongside `lint-imports-python`.

## Acceptance criteria

- [x] Script fails if a new file references the gateway port/host directly, unless added to the allowlist.
- [x] Script passes today — allowlist ended up as three files (`smoke.py`, `provider_evidence.py`, `release_evidence.py`) plus a `packages/llm_client/` exemption, not the two originally assumed; see done note above for why.
- [x] Added as a CI job (`lint-no-raw-gateway-calls`); the "why" is documented in the script's own module docstring (no `CONTRIBUTING.md` exists in this repo to put it in instead).

## Blocked by

Nothing.
