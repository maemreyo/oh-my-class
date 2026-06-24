---
title: "Token Budget: TB2 — TokenBudgetManager, EMA Adaptive, Soft/Hard Limits"
status: ready
labels: [architecture, llm, cost]
created: 2026-06-24
priority: p1
report: "04"
---

## What to build

Separate `token_budget` module — tracks token usage per task type, enforces soft limits (warn + log) vs hard limits (cap `max_tokens`), and adapts limits using exponential moving average over historical usage. Independent from `GateConfig` (SoC).

**Design decisions:**
- **TB2**: Separate module, not mixed into `gate-config`
- Soft limit: advisory — log warning when exceeded, do NOT truncate artifact
- Hard limit: passed as `max_tokens` to LLM — only for genuinely bounded tasks
- EMA adaptive: learns actual usage over time, starts from generous defaults
- Educational content defaults are generous (8K-12K output) — truncated artifacts are broken artifacts

## File Structure

```
packages/llm_client/budget/
├── __init__.py
├── config.py          # TokenBudgetConfig(BaseSettings) — BUDGET_ prefix
├── manager.py         # TokenBudgetManager: get_limit(), record_usage()
├── ema.py             # EMATracker: exponential moving average per task
└── tests/
    ├── test_manager.py
    └── test_ema.py
```

## Implementation Spec

### `budget/config.py`

```python
from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class TokenBudgetConfig(BaseSettings):
    """Token limits per task type.

    Two tiers:
      - soft_limit: log warning when exceeded, never truncate (educational content)
      - hard_limit: passed as max_tokens to LLM (short structured outputs only)

    Educational content defaults are generous — a truncated lesson/quiz is a broken artifact.
    Override via env: BUDGET_CONTENT_GENERATION_SOFT_LIMIT=15000
    """
    model_config = SettingsConfigDict(
        env_prefix="BUDGET_",
        env_file=".env",
        extra="ignore",
    )

    # Soft limits — warning only, never cap output
    content_generation_soft_limit: int = 12_000    # full lesson: 8K-12K typical
    blueprint_design_soft_limit: int = 6_000
    fact_verification_soft_limit: int = 4_000
    quality_gate_soft_limit: int = 3_000

    # Hard limits — passed as max_tokens (short, structured outputs)
    summarization_hard_limit: int = 800
    title_generation_hard_limit: int = 100
    schema_rewrite_hard_limit: int = 2_000
    content_review_light_hard_limit: int = 1_500

    # EMA configuration
    ema_alpha: float = 0.1          # smoothing factor — 0.1 = slow adaptation
    ema_headroom: float = 1.5       # soft limit = EMA × headroom
    ema_min_samples: int = 5        # EMA kicks in after N samples
```

### `budget/ema.py`

```python
"""Exponential Moving Average tracker for token usage per task type."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class EMATracker:
    """Tracks EMA of token usage. Starts with no data; uses fixed default until min_samples."""
    alpha: float = 0.1          # smaller = slower to adapt, more stable
    min_samples: int = 5        # require N samples before trusting EMA

    _values: dict[str, float] = field(default_factory=dict, repr=False)
    _counts: dict[str, int] = field(default_factory=dict, repr=False)

    def record(self, task: str, tokens: int) -> None:
        """Record actual token usage for a task."""
        count = self._counts.get(task, 0)
        current = self._values.get(task, float(tokens))

        if count == 0:
            self._values[task] = float(tokens)
        else:
            self._values[task] = self.alpha * tokens + (1 - self.alpha) * current

        self._counts[task] = count + 1

    def get_ema(self, task: str) -> float | None:
        """Return EMA value if enough samples collected, else None."""
        if self._counts.get(task, 0) < self.min_samples:
            return None
        return self._values.get(task)

    def sample_count(self, task: str) -> int:
        return self._counts.get(task, 0)
```

### `budget/manager.py`

```python
"""TokenBudgetManager: get limits and record usage for adaptive budgeting."""
from __future__ import annotations
import logging
from packages.llm_client.budget.config import TokenBudgetConfig
from packages.llm_client.budget.ema import EMATracker

logger = logging.getLogger(__name__)

# Tasks with soft limits (educational content — never hard-cap)
_SOFT_LIMIT_TASKS = {
    "content_generation", "blueprint_design",
    "fact_verification", "quality_gate",
}

# Tasks with hard limits (short structured outputs)
_HARD_LIMIT_TASKS = {
    "summarization", "title_generation",
    "schema_rewrite", "content_review_light",
}


class TokenBudgetManager:
    """Central token budget authority.

    Soft limits  → warn when exceeded, never truncate (educational content)
    Hard limits  → passed as max_tokens (short structured outputs)
    EMA adaptive → adjusts soft limits based on actual usage history
    """

    def __init__(self, config: TokenBudgetConfig | None = None):
        self._config = config or TokenBudgetConfig()
        self._ema = EMATracker(
            alpha=self._config.ema_alpha,
            min_samples=self._config.ema_min_samples,
        )

    def get_hard_limit(self, task: str) -> int | None:
        """Return max_tokens to pass to LLM. None = no cap (educational content)."""
        if task not in _HARD_LIMIT_TASKS:
            return None   # soft limit tasks: never cap output

        attr = f"{task}_hard_limit"
        return getattr(self._config, attr, None)

    def get_soft_limit(self, task: str) -> int:
        """Return advisory soft limit. EMA overrides fixed config after min_samples."""
        ema_value = self._ema.get_ema(task)
        if ema_value is not None:
            # EMA-based: historical average × headroom
            return int(ema_value * self._config.ema_headroom)

        attr = f"{task}_soft_limit"
        return getattr(self._config, attr, 8_000)   # fallback: 8K

    def check_soft_limit(self, task: str, tokens_used: int) -> bool:
        """Returns True if within soft limit. Logs warning if exceeded."""
        limit = self.get_soft_limit(task)
        if tokens_used > limit:
            logger.warning(
                "Token soft limit exceeded",
                extra={
                    "task": task,
                    "tokens_used": tokens_used,
                    "soft_limit": limit,
                    "overage_pct": round((tokens_used - limit) / limit * 100, 1),
                }
            )
            return False
        return True

    def record_usage(self, task: str, tokens_used: int) -> None:
        """Record actual usage for EMA adaptation."""
        self._ema.record(task, tokens_used)
        self.check_soft_limit(task, tokens_used)

    def summary(self) -> dict[str, dict]:
        """Return current limits and EMA state for all tracked tasks."""
        all_tasks = _SOFT_LIMIT_TASKS | _HARD_LIMIT_TASKS
        return {
            task: {
                "soft_limit": self.get_soft_limit(task),
                "hard_limit": self.get_hard_limit(task),
                "ema_samples": self._ema.sample_count(task),
                "ema_value": self._ema.get_ema(task),
            }
            for task in all_tasks
        }
```

### Usage in LLMClient

```python
# packages/llm_client/client.py (updated)

from packages.llm_client.budget.manager import TokenBudgetManager

_budget = TokenBudgetManager()   # module-level singleton

class LLMClient:
    async def chat(self, model, messages, task="unknown", **kwargs) -> ChatResponse:
        # Get hard limit if applicable (None for educational content)
        hard_limit = _budget.get_hard_limit(task)

        resp = await self._client.chat.completions.create(
            model=model,
            messages=...,
            max_tokens=hard_limit,   # None = let model generate freely
            **kwargs,
        )

        # Record usage for EMA adaptation
        _budget.record_usage(task, resp.usage.completion_tokens)

        return ChatResponse(...)
```

## Tests

```python
# tests/test_ema.py

from packages.llm_client.budget.ema import EMATracker

def test_ema_returns_none_before_min_samples():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    tracker.record("content_generation", 8000)
    tracker.record("content_generation", 9000)
    assert tracker.get_ema("content_generation") is None  # only 2 samples

def test_ema_returns_value_after_min_samples():
    tracker = EMATracker(alpha=0.1, min_samples=3)
    for tokens in [8000, 9000, 7500]:
        tracker.record("content_generation", tokens)
    assert tracker.get_ema("content_generation") is not None

def test_ema_adapts_toward_new_values():
    tracker = EMATracker(alpha=0.5, min_samples=1)
    tracker.record("task", 1000)
    tracker.record("task", 2000)   # alpha=0.5: new value pulls strongly
    ema = tracker.get_ema("task")
    assert 1000 < ema < 2000

# tests/test_manager.py

from packages.llm_client.budget.manager import TokenBudgetManager
from packages.llm_client.budget.config import TokenBudgetConfig

def test_content_generation_has_no_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("content_generation") is None

def test_summarization_has_hard_limit():
    manager = TokenBudgetManager()
    assert manager.get_hard_limit("summarization") == 800

def test_soft_limit_uses_config_before_ema_warmup():
    config = TokenBudgetConfig(content_generation_soft_limit=10_000)
    manager = TokenBudgetManager(config)
    assert manager.get_soft_limit("content_generation") == 10_000

def test_soft_limit_uses_ema_after_warmup():
    config = TokenBudgetConfig(ema_min_samples=2, ema_alpha=1.0, ema_headroom=1.5)
    manager = TokenBudgetManager(config)
    manager.record_usage("content_generation", 6000)
    manager.record_usage("content_generation", 6000)
    # EMA = 6000, headroom 1.5x → soft limit = 9000
    assert manager.get_soft_limit("content_generation") == 9000

def test_check_soft_limit_logs_warning(caplog):
    import logging
    manager = TokenBudgetManager(TokenBudgetConfig(content_generation_soft_limit=5000))
    with caplog.at_level(logging.WARNING):
        result = manager.check_soft_limit("content_generation", 6000)
    assert result is False
    assert "soft limit exceeded" in caplog.text.lower()

def test_hard_limit_tasks_never_return_none():
    manager = TokenBudgetManager()
    for task in ["summarization", "title_generation", "schema_rewrite"]:
        assert manager.get_hard_limit(task) is not None
```

## Acceptance Criteria

- [ ] `TokenBudgetConfig` — `BUDGET_` prefix, separate from `GateConfig`
- [ ] Educational content tasks (`content_generation`, `blueprint_design`) → `get_hard_limit()` returns `None` (never truncate)
- [ ] Structured output tasks (`summarization`, `title_generation`) → `get_hard_limit()` returns configured int
- [ ] `EMATracker` returns `None` before `min_samples` collected
- [ ] After `min_samples`: soft limit = EMA × headroom (overrides config value)
- [ ] `TokenBudgetManager.record_usage()` updates EMA and checks soft limit
- [ ] Soft limit exceeded → `WARNING` logged with task, tokens_used, overage_pct
- [ ] `summary()` returns state of all tracked tasks
- [ ] `LLMClient.chat()` passes `max_tokens=None` for educational content tasks

## Dependencies

- Blocked by: `llm-client` (LLMClient.chat() calls budget manager)
- Blocks: nothing (monitoring/cost visibility only — non-blocking)
- Priority: p1
