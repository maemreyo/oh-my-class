from __future__ import annotations

from services.gateway.main import _worker_runtime_config


def test_worker_runtime_config_uses_in_process_defaults_when_env_absent(monkeypatch) -> None:
    monkeypatch.delenv("WORKER_MODE", raising=False)
    monkeypatch.delenv("WORKER_CONCURRENCY", raising=False)

    config = _worker_runtime_config()

    assert config.mode == "in_process"
    assert config.concurrency == 1


def test_worker_runtime_config_accepts_external_mode_and_concurrency(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_MODE", "external")
    monkeypatch.setenv("WORKER_CONCURRENCY", "4")

    config = _worker_runtime_config()

    assert config.mode == "external"
    assert config.concurrency == 4


def test_worker_runtime_config_clamps_invalid_concurrency(monkeypatch) -> None:
    monkeypatch.setenv("WORKER_CONCURRENCY", "0")

    config = _worker_runtime_config()

    assert config.concurrency == 1
