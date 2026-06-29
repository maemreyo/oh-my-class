from __future__ import annotations

from threading import Lock

import anyio

from services.gateway.teaching_pack_types import RunId

_WAITERS: dict[str, list[anyio.Event]] = {}
_VERSIONS: dict[str, int] = {}
_EVENT_BUS_LOCK = Lock()


def current_run_event_version(run_id: RunId) -> int:
    with _EVENT_BUS_LOCK:
        return _VERSIONS.get(str(run_id), 0)


def notify_run_event(run_id: RunId) -> None:
    run_key = str(run_id)
    with _EVENT_BUS_LOCK:
        _VERSIONS[run_key] = _VERSIONS.get(run_key, 0) + 1
        waiters = _WAITERS.pop(run_key, [])
    for waiter in waiters:
        waiter.set()


async def wait_for_run_event(run_id: RunId, observed_version: int, timeout_seconds: float) -> bool:
    run_key = str(run_id)
    waiter = anyio.Event()
    with _EVENT_BUS_LOCK:
        if _VERSIONS.get(run_key, 0) > observed_version:
            return True
        _WAITERS.setdefault(run_key, []).append(waiter)
    woke_up = False
    try:
        with anyio.move_on_after(timeout_seconds):
            await waiter.wait()
            woke_up = True
    finally:
        with _EVENT_BUS_LOCK:
            waiters = _WAITERS.get(run_key, [])
            if waiter in waiters:
                waiters.remove(waiter)
            if not waiters:
                _WAITERS.pop(run_key, None)
    return woke_up
