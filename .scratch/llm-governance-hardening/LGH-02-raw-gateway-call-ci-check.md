---
title: "Grep-based CI check: ban raw LLM-gateway host/port outside allowlisted probes"
status: ready-for-agent
labels: [governance, ci, llm]
created: 2026-07-08
priority: p3
epic: llm-governance-hardening
sequence: 2
---

> Produced from `.scratch/design-reflection-2026-07-08.md` grill session, section 1 follow-up. `import-linter` (see `LGH-01`) cannot distinguish "httpx used to probe the gateway" from "httpx used to bypass LLMClient" — both just import `httpx`, a general-purpose library. This needs a different, narrower mechanism.

## What to build

Currently exactly two files legitimately call the LLM gateway (`:20228`) directly via `httpx`, for health-check/release-evidence purposes rather than agent completions:
- `packages/agents/llm/smoke.py`
- `services/gateway/provider_evidence.py`

Add `scripts/check_no_raw_gateway_calls.py`: grep `packages/` + `services/` (excluding `tests/`) for the gateway host/port literal (`20228`, and `LLMClientConfig.base_url`'s default host if it changes), fail if found outside a hardcoded allowlist of the two files above. Wire it into CI (`.github/workflows/ci.yml`) alongside `lint-imports-python`.

## Acceptance criteria

- [ ] Script fails if a new file references the gateway port/host directly, unless added to the allowlist.
- [ ] Script passes today with exactly `smoke.py` and `provider_evidence.py` allowlisted.
- [ ] Added as a CI job; documented in `CONTRIBUTING`/repo docs that these two files are the only sanctioned exception, and why (health/release probes need to hit the gateway directly, not through `LLMClient`'s chat-completion abstraction).

## Blocked by

Nothing.
