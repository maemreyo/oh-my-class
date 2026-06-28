from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMClientConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "http://localhost:20128/v1"
    api_key: str = ""
    timeout_s: float = 600.0
    max_retries: int = 3
    temperature: float = 0.1
