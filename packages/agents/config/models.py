from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM connection config. Env prefix: LLM_"""

    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "http://localhost:20128/v1"
    api_key: str = ""
    timeout: float = 300.0
    max_retries: int = 0


class ModelAssignments(BaseSettings):
    """9Router combo per agent/task. Env prefix: MODEL_"""

    model_config = SettingsConfigDict(
        env_prefix="MODEL_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    lead_agent: str = "f.pro"
    planner: str = "f.pro"
    researcher: str = "f.pro"
    content_creator: str = "f.pro"
    reviewer: str = "f.pro"
    diagnostician: str = "f.pro"

    llm_judge: str = "f.pro"
    fact_verification: str = "f.pro"
    quality_gate: str = "f.pro"

    blueprint_design: str = "f.pro"
    content_generation: str = "f.pro"
    schema_rewrite: str = "f.pro"

    summarization: str = "f.pro"
    title_generation: str = "f.pro"
    content_review_light: str = "f.pro"


LLM = LLMConfig()
MODELS = ModelAssignments()
