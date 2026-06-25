"""Tests for LLMClientConfig — env var reading and defaults."""
from __future__ import annotations

from packages.llm_client.config import LLMClientConfig


def test_config_defaults():
    config = LLMClientConfig()
    assert config.base_url == "http://localhost:20128"
    assert config.api_key == "dummy"
    assert config.timeout_s == 120.0
    assert config.max_retries == 0
    assert config.temperature == 0.1


def test_config_reads_env_var(monkeypatch):
    monkeypatch.setenv("LLM_CLIENT_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LLM_CLIENT_API_KEY", "sk-test-key")
    config = LLMClientConfig()
    assert config.base_url == "http://litellm:4000"
    assert config.api_key == "sk-test-key"


def test_config_no_retry_by_default():
    config = LLMClientConfig()
    # 0 = no client-side retry; LiteLLM handles retries in production
    assert config.max_retries == 0


def test_config_timeout_override(monkeypatch):
    monkeypatch.setenv("LLM_CLIENT_TIMEOUT_S", "60.0")
    config = LLMClientConfig()
    assert config.timeout_s == 60.0
