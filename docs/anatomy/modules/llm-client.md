# Module: llm-client

**Path:** `packages/llm_client`
**Role:** Thin wrapper over `openai.AsyncOpenAI` injected into all agents. Provides cost attribution, budget tracking, circuit breaking, middleware pipeline, and mock testing.

## Public interface

- `LLMClient.chat(messages, *, model, temperature, ...)` → `ChatResponse` (`client.py:87`)
- `LLMClient.stream(messages, *, model, ...)` → async token stream
- `LLMClient.chat_via_streaming_transport(messages, ...)` → streaming transport with full middleware
- `MockLLMClient` — deterministic fake for tests (`mock.py`)
- `ChatMessage` — typed message union
- `ChatResponse` — `{ content, model, input_tokens, output_tokens, cached }`
- `TokenBudgetManager` — soft/hard token limits with EMA adaptation
- `CircuitBreaker` — 3-state per-provider breaker
- Error hierarchy: `TransientProviderError`, `PermanentProviderError`, `FreeTierExhaustedError`, `ProviderRateLimitError`, `ProviderTimeoutError`, `AllProvidersDownError`, `BadPromptError`

## Internal structure

- `client.py` (305 lines) — `LLMClient` main class: `chat()`, `stream()`, `chat_via_streaming_transport()`
- `config.py` — `LLMClientConfig` (pydantic-settings, env LLM_*): base URL default `localhost:20228`
- `errors.py` — Typed error hierarchy with `classify_openai_error()`
- `middleware.py` — `CallMiddlewareRunner`: PII scrub, unsafe content, JSON repair, locale check
- `tags.py` — `build_tags()` for LiteLLM cost attribution
- `mock.py` — `MockLLMClient` with `set_response()`, `call_count()`, `last_call()`
- `circuit_breaker.py` — 3-state breaker, delegates to `packages.agents.healing.circuit_breaker`
- `budget/` — TokenBudgetManager, TokenBudgetConfig (env BUDGET_*), EMATracker

### LLMClient call pipeline
```
chat() / stream() / chat_via_streaming_transport()
  → CircuitBreaker check (per-model)
  → MiddlewareRunner.before_call() (PII, cost tags, system coalescing)
  → build_tags() for cost attribution
  → TokenBudgetManager.get_hard_limit() for max_tokens
  → openai.AsyncOpenAI call (9Router at localhost:20228)
  → CircuitBreaker.record_success/failure
  → TokenBudgetManager.record_usage() (EMA adaptation)
  → MiddlewareRunner.after_call() (unsafe block, PII scrub, JSON repair)
  → ChatResponse
```

## Depends on

- **`agents`** — imports `packages.agents.healing.circuit_breaker.BreakerStore`, `LayeredCircuitBreaker` (`circuit_breaker.py`)
- external: `openai>=1.0.0`, `pydantic-settings>=2.14.2`

## Used by

- **`agents`** — all sub-agents use LLMClient via `AgentRuntime`

## Data & side effects

- Network: 9Router sidecar at `http://localhost:20228/v1` (sync/async)
- Config: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_TIMEOUT_S`, `LLM_MAX_RETRIES`, `LLM_TEMPERATURE`, `BUDGET_*`

---

_Traced from source on 2026-07-10. Files examined: all 21 files. The budget subsystem is the most architecturally interesting — soft vs hard limits with EMA-adaptive prediction._
