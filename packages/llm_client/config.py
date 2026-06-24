"""LLM client configuration.

Local dev:  LLM_CLIENT_BASE_URL=http://localhost:20128  (9Router direct)
Production: LLM_CLIENT_BASE_URL=http://litellm:4000    (LiteLLM layer)

Agents never need to know which one is active — single env var switches.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMClientConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLM_CLIENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    base_url: str = "http://localhost:20128"
    api_key: str = "dummy"          # 9Router accepts any key locally
    timeout_s: float = 120.0
    max_retries: int = 0            # no client-side retry — LiteLLM handles it in prod
    temperature: float = 0.1
