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

    lead_agent: str = "4omc"
    planner: str = "4omc"
    researcher: str = "4omc"
    content_creator: str = "4omc"
    reviewer: str = "4omc"
    diagnostician: str = "4omc"

    llm_judge: str = "4omc"
    fact_verification: str = "4omc"
    quality_gate: str = "4omc"

    blueprint_design: str = "4omc"
    content_generation: str = "4omc"
    schema_rewrite: str = "4omc"

    summarization: str = "4omc"
    title_generation: str = "4omc"
    content_review_light: str = "4omc"


class MaxTokensConfig(BaseSettings):
    """Per-agent max_tokens budget. Env prefix: MAX_TOKENS_

    Caps total output (thinking + content) so reasoning models
    can't burn unlimited tokens on reasoning.
    """

    model_config = SettingsConfigDict(
        env_prefix="MAX_TOKENS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    planner: int = 4096
    researcher: int = 4096
    content_creator: int = 8192
    diagnostician: int = 2048
    reviewer: int = 2048
    default: int = 4096


class NinerouterConfig(BaseSettings):
    """9Router web tool config. Env prefix: NINEROUTER_"""

    model_config = SettingsConfigDict(
        env_prefix="NINEROUTER_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    timeout: float = 30.0
    search_results: int = 5
    min_sources: int = 2
    fetch_limit_basic: int = 2
    fetch_limit_standard: int = 5
    fetch_limit_rigorous: int = 10
    content_truncate: int = 4000


LLM = LLMConfig()
MODELS = ModelAssignments()
MAX_TOKENS = MaxTokensConfig()
NINEROUTER = NinerouterConfig()
