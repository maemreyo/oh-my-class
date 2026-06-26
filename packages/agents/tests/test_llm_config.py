from __future__ import annotations

from packages.agents.config.models import LLM, MODELS


def test_llm_config_defaults() -> None:
    assert LLM.base_url == "http://localhost:20128/v1"
    assert LLM.timeout == 120.0
    assert LLM.max_retries == 0


def test_model_assignments_defaults() -> None:
    assert MODELS.lead_agent == "f.pro"
    assert MODELS.planner == "f.pro"
    assert MODELS.researcher == "f.pro"
    assert MODELS.content_creator == "f.pro"
    assert MODELS.reviewer == "f.pro"


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LLM_BASE_URL", "http://custom:9999/v1")
    monkeypatch.setenv("MODEL_PLANNER", "f.light")

    from importlib import reload

    from packages.agents.config import models

    reload(models)

    assert models.LLM.base_url == "http://custom:9999/v1"
    assert models.MODELS.planner == "f.light"
