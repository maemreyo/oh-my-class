from __future__ import annotations

import pytest

from services.gateway.autoscaler import (
    AutoscaleConfig,
    any_provider_breaker_open,
    apply_scale,
    compute_desired_replicas,
    effective_ceiling,
)


def _config(**overrides) -> AutoscaleConfig:
    defaults = dict(
        floor_replicas=1,
        max_replicas=5,
        jobs_per_worker=3,
        worker_concurrency=2,
        provider_max_concurrent_requests=40,
        breaker_providers=(),
        redis_url=None,
    )
    defaults.update(overrides)
    return AutoscaleConfig(**defaults)


def test_effective_ceiling_uses_smaller_of_configured_max_and_provider_budget() -> None:
    # provider budget 40 / concurrency 2 = 20, well above configured max 5
    assert effective_ceiling(_config()) == 5

    # provider budget now the binding constraint: 6 / 2 = 3
    assert effective_ceiling(_config(provider_max_concurrent_requests=6)) == 3


def test_effective_ceiling_never_drops_below_floor() -> None:
    config = _config(floor_replicas=4, provider_max_concurrent_requests=1, worker_concurrency=10)
    assert effective_ceiling(config) == 4


def test_desired_replicas_at_floor_when_queue_empty() -> None:
    assert compute_desired_replicas(0, _config(floor_replicas=2), breaker_open=False) == 2


def test_desired_replicas_scales_up_with_backlog() -> None:
    config = _config(jobs_per_worker=3, floor_replicas=1, max_replicas=10)
    # 7 jobs / 3 per worker -> ceil = 3
    assert compute_desired_replicas(7, config, breaker_open=False) == 3


def test_desired_replicas_clamped_at_ceiling() -> None:
    config = _config(jobs_per_worker=1, floor_replicas=1, max_replicas=4, provider_max_concurrent_requests=400)
    assert compute_desired_replicas(1000, config, breaker_open=False) == 4


def test_desired_replicas_pinned_to_floor_when_breaker_open() -> None:
    config = _config(floor_replicas=1, max_replicas=10)
    assert compute_desired_replicas(50, config, breaker_open=True) == 1


class _FakeBreakerStore:
    def __init__(self, states: dict[str, dict]) -> None:
        self._states = states

    def get(self, key: str):
        return self._states.get(key)


def test_any_provider_breaker_open_true_when_one_open(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_store = _FakeBreakerStore({"cb:provider:openai": {"state": "open"}})
    monkeypatch.setattr(
        "packages.agents.healing.redis_breaker_store.RedisBreakerStore.from_url",
        lambda url: fake_store,
    )
    assert any_provider_breaker_open(("openai", "anthropic"), "redis://localhost:6379") is True


def test_any_provider_breaker_open_false_when_all_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_store = _FakeBreakerStore({"cb:provider:openai": {"state": "closed"}})
    monkeypatch.setattr(
        "packages.agents.healing.redis_breaker_store.RedisBreakerStore.from_url",
        lambda url: fake_store,
    )
    assert any_provider_breaker_open(("openai",), "redis://localhost:6379") is False


def test_any_provider_breaker_open_fails_open_with_no_redis_url() -> None:
    assert any_provider_breaker_open(("openai",), None) is False


def test_any_provider_breaker_open_fails_open_when_store_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenStore:
        def get(self, key: str):
            raise OSError("connection refused")

    monkeypatch.setattr(
        "packages.agents.healing.redis_breaker_store.RedisBreakerStore.from_url",
        lambda url: _BrokenStore(),
    )
    assert any_provider_breaker_open(("openai",), "redis://localhost:6379") is False


def test_apply_scale_dry_run_does_not_invoke_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: calls.append(args))
    apply_scale(3, dry_run=True)
    assert calls == []


def test_apply_scale_invokes_docker_compose_scale(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def _fake_run(args, check):
        captured["args"] = args
        captured["check"] = check

    monkeypatch.setattr("subprocess.run", _fake_run)
    apply_scale(3, dry_run=False)
    assert captured["args"][:2] == ["docker", "compose"]
    assert "worker=3" in captured["args"]
    assert captured["check"] is True
