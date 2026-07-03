from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class FakeRedisStore:
    values: dict[str, dict[str, float | int | str]]

    def get(self, key: str) -> dict[str, float | int | str] | None:
        return self.values.get(key)

    def set(self, key: str, value: dict[str, float | int | str], _ttl_seconds: float) -> None:
        self.values[key] = value


class FailingRedisStore:
    def get(self, _key: str) -> dict[str, float | int | str] | None:
        raise ConnectionError("redis unavailable")

    def set(
        self,
        _key: str,
        _value: dict[str, float | int | str],
        _ttl_seconds: float,
    ) -> None:
        raise ConnectionError("redis unavailable")


def test_run_breaker_state_is_shared_by_redis_key() -> None:
    from packages.agents.healing.circuit_breaker import CircuitBreaker, CircuitOpenError

    store = FakeRedisStore({})
    first_worker = CircuitBreaker.run("run-1", threshold=1, store=store)
    second_worker = CircuitBreaker.run("run-1", threshold=1, store=store)

    with pytest.raises(ValueError):
        first_worker.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

    assert store.values["cb:run:run-1"]["state"] == "open"
    with pytest.raises(CircuitOpenError):
        second_worker.call(lambda: "blocked")


def test_run_breaker_isolates_other_runs() -> None:
    from packages.agents.healing.circuit_breaker import CircuitBreaker

    store = FakeRedisStore({})
    failing_run = CircuitBreaker.run("run-bad", threshold=1, store=store)
    healthy_run = CircuitBreaker.run("run-good", threshold=1, store=store)

    with pytest.raises(ValueError):
        failing_run.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

    assert healthy_run.call(lambda: "allowed") == "allowed"


def test_provider_breaker_uses_provider_scope_without_global_key() -> None:
    from packages.agents.healing.circuit_breaker import CircuitBreaker

    store = FakeRedisStore({})
    provider = CircuitBreaker.provider("f.light", threshold=1, store=store)

    with pytest.raises(ValueError):
        provider.call(lambda: (_ for _ in ()).throw(ValueError("provider down")))

    assert "cb:provider:f.light" in store.values
    assert not any(key.startswith("cb:global") for key in store.values)
    assert provider.coordinates_with_litellm is True


def test_redis_down_fails_open_for_blocking_decision() -> None:
    from packages.agents.healing.circuit_breaker import CircuitBreaker

    breaker = CircuitBreaker.run("run-open", threshold=1, store=FailingRedisStore())

    assert breaker.call(lambda: "allowed") == "allowed"


def test_trip_emits_observability_event_and_run_exhausts() -> None:
    from packages.agents.events import clear_run, get_run_events
    from packages.agents.healing.circuit_breaker import CircuitBreaker

    store = FakeRedisStore({})
    clear_run("run-event")
    breaker = CircuitBreaker.run("run-event", threshold=1, store=store)

    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError("fail")))

    events = get_run_events("run-event")
    assert events[-1]["event_type"] == "breaker_tripped"
    assert events[-1]["scope"] == "run"
    assert events[-1]["breaker_key"] == "cb:run:run-event"
    assert breaker.exhausted is True
