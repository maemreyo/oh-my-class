# Module: llm-client

**Path:** `packages/llm_client`
**Role:** LLM client wrapper — provides a unified async interface for calling LLMs through 9Router/LiteLLM proxy, with circuit breaker, token budget tracking, middleware pipeline, and cost attribution tags.

## Public interface

```python
# packages/llm_client/__init__.py
LLMClient               # Thin wrapper over openai.AsyncOpenAI
MockLLMClient           # Deterministic fake for agent tests
ChatMessage             # dataclass: role, content
ChatResponse            # dataclass: content, model, input_tokens, output_tokens, cached
CallMiddlewareRunner    # PII scrub, safety, JSON repair pipeline
build_tags()            # Cost attribution metadata for LiteLLM
```

### LLMClient (`client.py`)

```python
class LLMClient:
    def __init__(self, config: LLMClientConfig | None = None) -> None: ...
    async def chat(model, messages, agent, task, run_id, step, max_tokens, temperature, locale, response_format) -> ChatResponse
    async def stream(model, messages, agent, task, run_id, step, locale, max_tokens) -> AsyncIterator[str]
    async def chat_via_streaming_transport(model, messages, agent, task, run_id, step, max_tokens, temperature, locale) -> ChatResponse
```

Three call paths:
- `chat()` — Standard request/response with full middleware pipeline (before_call + after_call)
- `stream()` — Token-by-token streaming (before_call only; no after_call because partial tokens can't be validated)
- `chat_via_streaming_transport()` — Streaming HTTP transport but accumulates full response before after_call middleware. For callers needing streaming transport with full safety guarantees.

### MockLLMClient (`mock.py`)

```python
class MockLLMClient:
    def set_response(model, task, response) -> None   # Queue response for model+task
    def set_default(response) -> None                  # Fallback
    async def chat(model, messages, agent, task, run_id, **kwargs) -> ChatResponse
    async def stream(model, messages, agent, task, run_id, **kwargs) -> AsyncIterator[str]
    def call_count(model, task) -> int                 # Query call count
    def last_call() -> dict | None                     # Inspect last call
    def reset() -> None                                # Clear state
```

### LLMClientConfig (`config.py`)

```python
class LLMClientConfig(BaseSettings):      # env prefix: LLM_
    base_url: str = "http://localhost:20228/v1"   # 9Router default
    api_key: str = ""
    timeout_s: float = 600.0
    max_retries: int = 3
    temperature: float = 0.1
```

### Error hierarchy (`errors.py`)

```
LLMProviderError (base)
├── TransientProviderError (retryable)
│   ├── FreeTierExhaustedError   (retry_after: 300s)
│   ├── ProviderRateLimitError    (retry_after: 60s)
│   ├── ProviderTimeoutError      (retry_after: 30s)
│   └── AllProvidersDownError     (retry_after: 120s)
└── PermanentProviderError (non-retryable)
    └── BadPromptError
```

`classify_openai_error(exc)` maps `openai.*` exceptions to typed errors.

### CallMiddlewareRunner (`middleware.py`)

**before_call pipeline:**
1. `_check_cost_tags()` — rejects if agent/task are "unknown" (`BadPromptError`)
2. `_coalesce_system_messages()` — merges duplicate system messages
3. `_UNSAFE_PATTERN` check — blocks weapon/self-harm/suicide/pornographic content in input

**after_call pipeline:**
1. `_UNSAFE_PATTERN` check — blocks unsafe content in output (`PermanentProviderError`)
2. `_PII_PATTERN` scrub — redacts emails and student PII → `[redacted-pii]`
3. `_repair_json_payload()` — extracts JSON from markdown fences or raw text
4. Vietnamese locale marker check — flags if expected Vietnamese content lacks diacritics

### Circuit Breaker (`circuit_breaker.py`)

```python
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_seconds: float = 60.0
    def record_success() -> None
    def record_failure() -> None
    def is_open() -> bool       # True = provider is blocked
    def reset() -> None
    state: CircuitState          # "closed" | "open" | "half_open"

def breaker_for(provider) -> CircuitBreaker    # Per-provider singleton
def should_skip_provider(provider) -> bool
```

Delegates to `packages.agents.healing.circuit_breaker.LayeredCircuitBreaker` when a provider is named, with graceful fallback to local state.

### Token Budget (`budget/`)

```python
class TokenBudgetManager:
    def get_hard_limit(task) -> int | None     # max_tokens for structured tasks
    def get_soft_limit(task) -> int            # advisory limit (EMA-adaptive)
    def check_soft_limit(task, tokens_used) -> bool  # logs warning if exceeded
    def record_usage(task, tokens_used) -> None
    def summary() -> dict

class EMATracker:                              # Exponential Moving Average
    def record(task, tokens) -> None
    def get_ema(task) -> float | None          # None until min_samples reached
```

**Soft limits** (educational content — warn, never cap): content_generation=12K, blueprint_design=6K, fact_verification=4K, quality_gate=3K
**Hard limits** (structured outputs — passed as max_tokens): summarization=800, title_generation=100, schema_rewrite=2K, content_review_light=1.5K

## Internal structure

```
packages/llm_client/
├── __init__.py              # Public API: 6 exports
├── client.py                # LLMClient class (main wrapper, ~270 lines)
├── config.py                # LLMClientConfig (pydantic-settings, env LLM_*)
├── errors.py                # Typed error hierarchy + classify_openai_error()
├── middleware.py            # CallMiddlewareRunner (PII scrub, safety, JSON repair)
├── mock.py                  # MockLLMClient for tests
├── tags.py                  # build_tags() for cost attribution
├── circuit_breaker.py       # Per-provider circuit breaker (delegates to agents.healing)
├── budget/
│   ├── __init__.py
│   ├── config.py            # TokenBudgetConfig (env BUDGET_*)
│   ├── ema.py               # EMATracker (EMA with configurable alpha)
│   └── manager.py           # TokenBudgetManager
├── tests/
│   ├── test_client.py
│   ├── test_middleware.py
│   ├── test_mock.py
│   └── test_tags.py
└── pyproject.toml
```

### LLMClient call pipeline

```
chat() / stream() / chat_via_streaming_transport()
  → breaker_for(model).is_open() → ProviderCircuitOpenError if open
  → MiddlewareRunner.before_call() (cost tags check, system coalescing, unsafe content)
  → build_tags() for LiteLLM cost attribution
  → TokenBudgetManager.get_hard_limit() for max_tokens
  → openai.AsyncOpenAI.chat.completions.create() → 9Router at :20228
  → CircuitBreaker.record_success/record_failure
  → TokenBudgetManager.record_usage() → EMA adaptation
  → MiddlewareRunner.after_call() (unsafe block, PII scrub, JSON repair, locale check)
  → ChatResponse
```

## Depends on

| Target | What | Where cited |
|--------|------|-------------|
| `packages.agents.healing.circuit_breaker` | `BreakerStore`, `CircuitBreaker as LayeredCircuitBreaker` | `circuit_breaker.py:5-7` |
| `openai` | `AsyncOpenAI`, `OpenAIError`, typed exceptions | `client.py:5,8`; `errors.py` |
| `pydantic_settings` | `BaseSettings`, `SettingsConfigDict` | `config.py:3-4`; `budget/config.py` |

### Boundary verification (Phase 3 hypothesis: "llm-client → agents: 1 import")

**CONFIRMED.** `circuit_breaker.py:5-7` imports from `packages.agents.healing.circuit_breaker`:

```python
from packages.agents.healing.circuit_breaker import (
    BreakerStore,
    CircuitBreaker as LayeredCircuitBreaker,
)
```

This is a **reverse dependency violation** — llm_client sits below agents in the dependency hierarchy. The import delegates provider-scoped circuit breaking to the healing subsystem's `LayeredCircuitBreaker.provider()` factory, with a graceful fallback to local state when the delegate is unavailable.

**Risk:** Creates circular dependency risk if agents.healing ever imports from llm_client. Currently safe because the import is inside a method, not at module level. However, the `pyproject.toml` does NOT declare this dependency — it's an implicit runtime dependency via sys.path manipulation.

## Used by

| Consumer | What imported | Where |
|----------|---------------|-------|
| **agents (all sub-agents)** | `LLMClient` via `AgentRuntime` | `sub_agents/*/agent.py` |
| **agents (teaching_pack)** | `LLMClient` for LLM calls | `teaching_pack/graph.py`, `nodes.py` |
| **agents (middleware)** | `CallMiddlewareRunner` | Various middleware files |
| **quality** | `ChatMessage`, `LLMClient` (lazy) | `layer4_judge/judge_transport.py:34` |
| **gateway** | Instantiates `LLMClient` with config | `services/gateway/main.py` |
| **tests** | `MockLLMClient` | Various test files |

## Data & side effects

- **Network:** Connects to LLM endpoint (9Router `:20228` default, or LiteLLM `:4000`)
- **Config:** Reads `LLM_*` env vars (base_url, api_key, timeout_s, max_retries, temperature)
- **Config:** Reads `BUDGET_*` env vars for token limits
- **State:** Module-level `_budget = TokenBudgetManager()` singleton
- **State:** Module-level `_breakers: dict[str, CircuitBreaker]` per-provider breaker map
- **Logging:** Budget manager logs warnings when soft limits exceeded

## Notes / discrepancies vs existing docs

- **Boundary issue confirmed:** llm_client imports from agents.healing.circuit_breaker (`circuit_breaker.py:5-7`). This violates INVARIANT-02 architectural intent. The import is guarded by a fallback (`if self.provider is None: return None`) so it degrades gracefully.
- **`pyproject.toml` doesn't list `packages.agents.healing` as dependency** — only `openai>=1.0.0` and `pydantic-settings>=2.14.2` are declared. The agents dependency is implicit via sys.path.
- AGENTS.md §6 says "9Router direct is default" — **confirmed** by `config.py:8`: `base_url = "http://localhost:20228/v1"` (9Router port).
- **`MiddlewareCallContext` requires agent and task to be non-"unknown"** — the `before_call` middleware raises `BadPromptError("missing_cost_tag_context")` if either is "unknown". This enforces INVARIANT-07 (all LLM calls MUST include metadata tags).

---
_Traced from source on 2026-07-11. Files examined in depth: all 14 source + 4 test files in packages/llm_client/. Key finding: boundary violation with agents.healing.circuit_breaker (circuit_breaker.py:5-7) — reverse dependency from lower-level package to higher-level._
