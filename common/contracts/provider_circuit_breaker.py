from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol


class BreakerStore(Protocol):
    def get(self, key: str) -> dict[str, float | int | str] | None: ...

    def set(self, key: str, value: dict[str, float | int | str], ttl_seconds: float) -> None: ...


@dataclass(frozen=True, slots=True)
class ProviderCircuitBreaker:
    provider_name: str
    threshold: int = 3
    recovery_timeout: float = 60.0
    store: BreakerStore | None = None

    @classmethod
    def provider(
        cls,
        provider: str,
        *,
        threshold: int = 3,
        recovery_timeout: float = 60.0,
        store: BreakerStore | None = None,
    ) -> ProviderCircuitBreaker:
        return cls(provider, threshold, recovery_timeout, store)

    @property
    def state(self) -> str:
        return str(self._state()["state"])

    def is_open(self) -> bool:
        current = self._state()
        if current["state"] != "open":
            return False
        if time.time() - float(current["last_failure_time"]) >= self.recovery_timeout:
            self._save({**current, "state": "half-open"})
            return False
        return True

    def record_success(self) -> None:
        self._save({"failures": 0, "state": "closed", "last_failure_time": 0.0})

    def record_failure(self) -> None:
        current = self._state()
        failures = int(current["failures"]) + 1
        self._save({
            "failures": failures,
            "state": "open" if failures >= self.threshold else "closed",
            "last_failure_time": time.time(),
        })

    def _state(self) -> dict[str, float | int | str]:
        if self.store is None:
            return {"failures": 0, "state": "closed", "last_failure_time": 0.0}
        stored = self.store.get(f"cb:provider:{self.provider_name}")
        return stored or {"failures": 0, "state": "closed", "last_failure_time": 0.0}

    def _save(self, value: dict[str, float | int | str]) -> None:
        if self.store is not None:
            self.store.set(f"cb:provider:{self.provider_name}", value, self.recovery_timeout)
