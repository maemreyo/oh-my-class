from __future__ import annotations

from packages.agents.llm import get_llm_config, resolve_model


def test_resolve_model_routes_all_known_aliases_to_f_pro() -> None:
    aliases = [
        "f.light",
        "f.pro",
        "gpt-5.4",
        "deepseek-v4-flash",
        "deepseek-free",
        "content-fusion",
        "deepseek-compressed",
        "deepseek-direct",
    ]

    for alias in aliases:
        assert resolve_model(alias) == "openai/f.pro"


def test_get_llm_config_uses_9router_when_litellm_env_is_set(monkeypatch) -> None:
    monkeypatch.setenv("LITELLM_API_BASE", "http://localhost:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "litellm-key")
    monkeypatch.setenv("NINEROUTER_API_KEY", "router-key")
    monkeypatch.delenv("NINEROUTER_BASE_URL", raising=False)

    config = get_llm_config()

    assert config == {
        "api_base": "http://localhost:20128/v1",
        "api_key": "router-key",
    }
