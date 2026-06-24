"""9Router model assignments for oh-my-class.

Combos match AGENTS.md §6.1 model assignment table:
  f.pro   → gpt-5.4 / content-fusion (Lead, Judge, Fact-check)
  f.light → deepseek-v4-flash / deepseek-free (Planner, Researcher, Content Creator)

Override via env: MODEL_BLUEPRINT_DESIGN=f.pro
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

    # f.pro — judgment / synthesis (gpt-5.4 / content-fusion per §6.1)
    lead_agent: str = "f.pro"
    llm_judge: str = "f.pro"
    fact_verification: str = "f.pro"

    # f.light — fast generation (deepseek-v4-flash / deepseek-free per §6.1)
    blueprint_design: str = "f.light"
    researcher: str = "f.light"
    content_generation: str = "f.light"
    schema_rewrite: str = "f.light"
    summarization: str = "f.light"
    title_generation: str = "f.light"
    content_review_light: str = "f.light"


# Singleton — import this, not ModelConfig()
MODELS = ModelConfig()
