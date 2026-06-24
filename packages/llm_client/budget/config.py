"""Token budget configuration.

Separate from GateConfig (SoC): different concern — cost tracking, not quality thresholds.
Override via env: BUDGET_CONTENT_GENERATION_SOFT_LIMIT=15000
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class TokenBudgetConfig(BaseSettings):
    """Token limits per task type.

    Two tiers:
      - soft_limit: log warning when exceeded, never truncate (educational content)
      - hard_limit: passed as max_tokens to LLM (short structured outputs only)

    Educational content defaults are generous — a truncated lesson/quiz is a broken artifact.
    """

    model_config = SettingsConfigDict(
        env_prefix="BUDGET_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
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
