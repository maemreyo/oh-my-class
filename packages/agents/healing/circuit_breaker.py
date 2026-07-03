from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol


class CircuitOpenError(Exception):
    pass


class BreakerStore(Protocol):
    def get(self, key: str) -> dict[str, float | int | str] | None: ...

    def set(self, key: str, value: dict[str, float | int | str], ttl_seconds: float) -> None: ...


@dataclass(frozen=True, slots=True)
class BreakerScope:
    name: str
    identifier: str

    @property
    def key(self) -> str:
        return f"cb:{self.name}:{self.identifier}"


@dataclass(frozen=True, slots=True)
class BreakerState:
    failures: int = 0
    state: str = "closed"
    last_failure_time: float = 0.0

    @classmethod
    def from_mapping(cls, value: dict[str, float | int | str] | None) -> BreakerState:
        if value is None:
            return cls()
        return cls(
            failures=int(value.get("failures", 0)),
            state=str(value.get("state", "closed")),
            last_failure_time=float(value.get("last_failure_time", 0.0)),
        )

    def as_mapping(self) -> dict[str, float | int | str]:
        return {
            "failures": self.failures,
            "state": self.state,
            "last_failure_time": self.last_failure_time,
        }


class NullBreakerStore:
    def get(self, _key: str) -> dict[str, float | int | str] | None:
        return None

    def set(
        self,
        _key: str,
        _value: dict[str, float | int | str],
        _ttl_seconds: float,
    ) -> None:
        return None


class InMemoryBreakerStore:
    def __init__(self) -> None:
        self._values: dict[str, dict[str, float | int | str]] = {}

    def get(self, key: str) -> dict[str, float | int | str] | None:
        return self._values.get(key)

    def set(self, key: str, value: dict[str, float | int | str], _ttl_seconds: float) -> None:
        self._values[key] = value


class CircuitBreaker:
    def __init__(
        self,
        threshold: int | None = None,
        recovery_timeout: float | None = None,
        *,
        scope: BreakerScope | None = None,
        store: BreakerStore | None = None,
        coordinates_with_litellm: bool = False,
    ) -> None:
        from packages.agents.config.gate_config import GateConfig

        config = GateConfig()
        self.threshold = threshold if threshold is not None else config.schema_circuit_threshold
        self.recovery_timeout = (
            recovery_timeout if recovery_timeout is not None else config.schema_circuit_recovery_s
        )
        self._scope = scope or BreakerScope("run", "local")
        self._store = store or InMemoryBreakerStore()
        self.coordinates_with_litellm = coordinates_with_litellm

    @classmethod
    def run(
        cls,
        run_id: str,
        threshold: int | None = None,
        recovery_timeout: float | None = None,
        *,
        store: BreakerStore | None = None,
    ) -> CircuitBreaker:
        return cls(
            threshold=threshold,
            recovery_timeout=recovery_timeout,
            scope=BreakerScope("run", run_id),
            store=store or _default_store(),
        )

    @classmethod
    def provider(
        cls,
        provider: str,
        threshold: int | None = None,
        recovery_timeout: float | None = None,
        *,
        store: BreakerStore | None = None,
    ) -> CircuitBreaker:
        return cls(
            threshold=threshold,
            recovery_timeout=recovery_timeout,
            scope=BreakerScope("provider", provider),
            store=store or _default_store(),
            coordinates_with_litellm=True,
        )

    @property
    def state(self) -> str:
        return self._load_state().state

    @property
    def failures(self) -> int:
        return self._load_state().failures

    @property
    def exhausted(self) -> bool:
        current = self._load_state()
        return current.state == "open" and current.failures >= self.threshold

    def call[T](self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        current = self._load_state()
        if self._blocks(current):
            wait_seconds = max(0.0, self.recovery_timeout - (time.time() - current.last_failure_time))
            raise CircuitOpenError(f"Circuit open — wait {wait_seconds:.0f}s before retry")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result

    def record_success(self) -> None:
        self._save_state(BreakerState())

    def record_failure(self) -> None:
        current = self._load_state()
        failures = current.failures + 1
        next_state = "open" if failures >= self.threshold else "closed"
        opened = current.state != "open" and next_state == "open"
        updated = BreakerState(
            failures=failures,
            state=next_state,
            last_failure_time=time.time(),
        )
        self._save_state(updated)
        if opened:
            self._emit_trip(updated)

    def _blocks(self, current: BreakerState) -> bool:
        if current.state != "open":
            return False
        if time.time() - current.last_failure_time > self.recovery_timeout:
            self._save_state(BreakerState(
                failures=current.failures,
                state="half-open",
                last_failure_time=current.last_failure_time,
            ))
            return False
        return True

    def _load_state(self) -> BreakerState:
        try:
            return BreakerState.from_mapping(self._store.get(self._scope.key))
        except (ConnectionError, OSError):
            return BreakerState()

    def _save_state(self, state: BreakerState) -> None:
        try:
            self._store.set(self._scope.key, state.as_mapping(), self.recovery_timeout)
        except (ConnectionError, OSError):
            return

    def _emit_trip(self, state: BreakerState) -> None:
        from packages.agents.events import emit_run_event

        payload = {
            "scope": self._scope.name,
            "breaker_key": self._scope.key,
            "state": state.state,
            "failures": state.failures,
            "coordinates_with_litellm": self.coordinates_with_litellm,
        }
        run_id = self._scope.identifier if self._scope.name == "run" else f"provider:{self._scope.identifier}"
        emit_run_event(run_id, "breaker_tripped", payload)


def _default_store() -> BreakerStore:
    from packages.agents.healing.redis_breaker_store import RedisBreakerStore

    return RedisBreakerStore.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
