"""TokenBudgetManager: get limits and record usage for adaptive budgeting."""
from __future__ import annotations

import logging

from packages.llm_client.budget.config import TokenBudgetConfig
from packages.llm_client.budget.ema import EMATracker

logger = logging.getLogger(__name__)

# Tasks with soft limits (educational content — never hard-cap)
_SOFT_LIMIT_TASKS: frozenset[str] = frozenset({
    "content_generation",
    "blueprint_design",
    "fact_verification",
    "quality_gate",
})

# Tasks with hard limits (short structured outputs)
_HARD_LIMIT_TASKS: frozenset[str] = frozenset({
    "summarization",
    "title_generation",
    "schema_rewrite",
    "content_review_light",
})


class TokenBudgetManager:
    """Central token budget authority.

    Soft limits  → warn when exceeded, never truncate (educational content)
    Hard limits  → passed as max_tokens (short structured outputs)
    EMA adaptive → adjusts soft limits based on actual usage history
    """

    def __init__(self, config: TokenBudgetConfig | None = None) -> None:
        self._config = config or TokenBudgetConfig()
        self._ema = EMATracker(
            alpha=self._config.ema_alpha,
            min_samples=self._config.ema_min_samples,
        )

    def get_hard_limit(self, task: str) -> int | None:
        """Return max_tokens to pass to LLM. None = no cap (educational content)."""
        if task not in _HARD_LIMIT_TASKS:
            return None

        attr = f"{task}_hard_limit"
        return getattr(self._config, attr, None)

    def get_soft_limit(self, task: str) -> int:
        """Return advisory soft limit. EMA overrides fixed config after min_samples."""
        ema_value = self._ema.get_ema(task)
        if ema_value is not None:
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
                },
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
            for task in sorted(all_tasks)
        }
