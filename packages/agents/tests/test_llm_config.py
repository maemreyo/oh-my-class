from __future__ import annotations

from packages.agents.config.models import MODELS
from packages.llm_client.config import LLMClientConfig


def test_llm_client_config_defaults() -> None:
    assert LLMClientConfig().base_url == "http://localhost:20228/v1"  # 9router port
    assert LLMClientConfig().timeout_s == 600.0
    assert LLMClientConfig().max_retries == 3


def test_model_assignments_defaults() -> None:
    assert MODELS.planner == "4omc"
    assert MODELS.researcher == "4omc"
    assert MODELS.content_creator == "4omc"
    assert MODELS.reviewer == "4omc"


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://custom:9999/v1")
    monkeypatch.setenv("MODEL_PLANNER", "4omc-experimental")

    from importlib import reload

    from packages.agents.config import models

    reload(models)

    assert LLMClientConfig().base_url == "http://custom:9999/v1"
    assert models.MODELS.planner == "4omc-experimental"
