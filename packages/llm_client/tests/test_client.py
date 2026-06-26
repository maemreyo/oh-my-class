from __future__ import annotations

from packages.llm_client.config import LLMClientConfig


def test_config_reads_from_centralized_llm_config() -> None:
    config = LLMClientConfig()
    assert config.base_url == "http://localhost:20128/v1"
    assert config.timeout_s == 600.0
    assert config.max_retries == 0
    assert config.temperature == 0.1


def test_config_uses_llm_env_vars(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LLM_API_KEY", "sk-test-key")

    from importlib import reload

    from packages.agents.config import models

    reload(models)

    from packages.llm_client.config import LLMClientConfig

    config = LLMClientConfig()
    assert config.base_url == "http://litellm:4000"
    assert config.api_key == "sk-test-key"
