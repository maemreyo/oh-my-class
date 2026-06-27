# Task 1: Live 9Router Chat Smoke Harness + Configurable Target

## Status: **pass**

## Summary

Implemented a deterministic smoke harness (`packages/agents/llm/smoke.py`) that probes
`/v1/models` and `/v1/chat/completions` against a configurable 9Router target.
All probes return structured `SmokeResult` — never raise on network errors.

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `packages/agents/llm/smoke.py` | **created** | 163 |
| `packages/agents/tests/llm/test_smoke.py` | **created** | 224 |

## Implementation Details

### SmokeConfig (configurable target)
- `base_url`: default `http://127.0.0.1:20228`, configurable via constructor or env
- `model`: default `4omc`, configurable per probe
- `timeout_s`: default `10.0s`
- Trailing slash stripped automatically

### SmokeResult (structured outcome)
- `status`: `"pass"` | `"blocked"` | `"fail"`
- `models_endpoint_ok`, `chat_endpoint_ok`: granular endpoint health
- `model_used`: confirmed model string from server
- `elapsed_s`: wall-clock probe time
- `error`: human-readable error detail (never None on non-pass)

### smoke_probe (async entry point)
- Step 1: GET `/v1/models` — connectivity + health check
- Step 2: POST `/v1/chat/completions` — actual inference check
- `stream: false` forced to avoid SSE parsing
- Accepts `reasoning_content` as valid response (reasoning models)
- `_client` injection point for deterministic testing

## Test Coverage (16 tests, all passing)

| Category | Tests | Status |
|----------|-------|--------|
| SmokeConfig defaults/override | 3 | pass |
| SmokeResult structure | 2 | pass |
| Unreachable service → blocked | 2 | pass |
| Mock server → pass / blocked | 2 | pass |
| Malformed JSON → blocked | 1 | pass |
| Misleading success → blocked/fail | 2 | pass |
| Timeout simulation → blocked | 2 | pass |
| Bad input → blocked | 2 | pass |

### Adversarial Classes Covered
- **Malformed input**: empty base_url, non-http scheme
- **Dirty worktree**: N/A (no file I/O in smoke harness)
- **Misleading success**: 200 with wrong JSON structure, empty choices
- **Hung external command**: simulated via ConnectTimeout / ReadTimeout exceptions
- **Malformed JSON response**: garbled body that fails json.JSONDecodeError

## Manual QA — Live 9Router Probe

### /v1/models
```
GET http://127.0.0.1:20228/v1/models
Status: 200 OK
Models found: 78 (including 4omc, f.pro, f.light, visual-inspector, x.fast)
```

### /v1/chat/completions
```
POST http://127.0.0.1:20228/v1/chat/completions
Body: {"model":"4omc","messages":[{"role":"user","content":"ping"}],"max_tokens":8,"stream":false}
Status: 200 OK
Model used: minimax-m3 (4omc routes to minimax-m3)
Response: reasoning_content="The user sent \"ping\". This"
Content: "" (empty — reasoning model pattern)
```

**Note**: 9Router `4omc` model routes to `minimax-m3` which is a reasoning model.
The smoke harness correctly handles this by accepting `reasoning_content` as valid response.

## Ruff / Lint
```
All checks passed!
2 files already formatted
```

## LOC Check
| File | Pure LOC | Verdict |
|------|----------|---------|
| `smoke.py` | 163 | Healthy |
| `test_smoke.py` | 224 | Healthy |

## Risks
1. **9Router model routing**: `4omc` maps to `minimax-m3` (reasoning model) — the smoke
   harness handles this, but downstream consumers should be aware the model string in
   `SmokeResult.model_used` reflects the configured name, not the actual backend model.
2. **SSE default**: 9Router defaults to streaming; the harness forces `stream: false`.
   If a future 9Router version ignores this flag, the probe will return "blocked" with
   a JSON parse error — safe degradation.
3. **No paid fallbacks**: The harness uses no fallback chains. If 9Router is down, the
   result is "blocked" — never falls back to a paid provider.
