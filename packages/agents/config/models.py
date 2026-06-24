"""9Router model assignments for oh-my-class.

Rule: f.pro for heavy reasoning/generation/judgment,
      f.light for fast/cheap/repetitive tasks.

Override via env: MODEL_CONTENT_GENERATION=f.light
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseSettings):
    """9Router combo names for each task type."""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Heavy tasks (f.pro — best quality free tier)
    blueprint_design: str = "f.pro"
    content_generation: str = "f.pro"
    llm_judge: str = "f.pro"
    fact_verification: str = "f.pro"
    researcher: str = "f.pro"

    # Light tasks (f.light — fast/cheap)
    schema_rewrite: str = "f.light"
    summarization: str = "f.light"
    title_generation: str = "f.light"
    content_review_light: str = "f.light"


# Singleton — import this, not ModelConfig()
MODELS = ModelConfig()
