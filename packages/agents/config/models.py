"""9Router model assignments for oh-my-class.

Temporary dev routing uses f.pro for every task.

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
    # Alias: spec QG2 references MODELS.quality_gate → resolves to same f.pro combo
    quality_gate: str = "f.pro"

    blueprint_design: str = "f.pro"
    researcher: str = "f.pro"
    content_generation: str = "f.pro"
    schema_rewrite: str = "f.pro"
    summarization: str = "f.pro"
    title_generation: str = "f.pro"
    content_review_light: str = "f.pro"


# Singleton — import this, not ModelConfig()
MODELS = ModelConfig()
