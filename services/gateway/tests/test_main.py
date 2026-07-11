from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI

from services.gateway import main as gateway_main

if TYPE_CHECKING:
    from collections.abc import Callable

    from anyio.abc import TaskGroup


class _FakeEngine:
    async def dispose(self) -> None:
        return None


async def _fake_get_checkpointer(environment: str, **kwargs: object) -> object:
    _ = (environment, kwargs)
    return object()


class TestMainLifespan:
    def test_lifespan_starts_teaching_pack_worker_and_recovery_sweeper(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        anyio.run(_assert_lifespan_starts_background_tasks, monkeypatch)

    def test_cors_preflight_reaches_teaching_pack_routes_without_auth(self) -> None:
        from starlette.testclient import TestClient

        response = TestClient(gateway_main.app).options(
            "/teaching-packs/runs/example-run",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    def test_gateway_does_not_register_legacy_graph_state(self, monkeypatch: pytest.MonkeyPatch) -> None:
        anyio.run(_assert_lifespan_skips_legacy_graph, monkeypatch)


async def _assert_lifespan_starts_background_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sweeper_started = anyio.Event()
    worker_started = anyio.Event()

    async def record_sweeper(_app: FastAPI) -> None:
        sweeper_started.set()
        await anyio.sleep_forever()

    async def record_worker(_app: FastAPI, _task_group: TaskGroup) -> None:
        worker_started.set()
        await anyio.sleep_forever()

    def fake_sessionmaker(engine: _FakeEngine, expire_on_commit: bool) -> Callable[[], object]:
        _ = (engine, expire_on_commit)
        return object

    monkeypatch.setattr(gateway_main, "configure_logging", lambda **kwargs: None)
    monkeypatch.setattr(gateway_main, "_run_teaching_pack_sweeper", record_sweeper)
    monkeypatch.setattr(gateway_main, "_run_teaching_pack_worker", record_worker)
    monkeypatch.setenv("OMC_ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

    import packages.agents.checkpointer as checkpointer_module
    import packages.agents.teaching_pack.graph as teaching_pack_graph_module
    import services.gateway.teaching_pack_runtime as teaching_pack_runtime_module

    monkeypatch.setattr(teaching_pack_runtime_module, "create_async_engine", lambda url, pool_pre_ping: _FakeEngine())
    monkeypatch.setattr(teaching_pack_runtime_module, "async_sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(checkpointer_module, "get_checkpointer", _fake_get_checkpointer)
    monkeypatch.setattr(teaching_pack_graph_module, "build_teaching_pack_graph", lambda **kwargs: object())

    app = FastAPI()
    async with gateway_main.lifespan(app):
        with anyio.fail_after(1):
            await sweeper_started.wait()
            await worker_started.wait()


async def _assert_lifespan_skips_legacy_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    async def record_sweeper(_app: FastAPI) -> None:
        await anyio.sleep_forever()

    async def record_worker(_app: FastAPI, _task_group: TaskGroup) -> None:
        await anyio.sleep_forever()

    def fake_sessionmaker(engine: _FakeEngine, expire_on_commit: bool) -> Callable[[], object]:
        _ = (engine, expire_on_commit)
        return object

    monkeypatch.setattr(gateway_main, "configure_logging", lambda **kwargs: None)
    monkeypatch.setattr(gateway_main, "_run_teaching_pack_sweeper", record_sweeper)
    monkeypatch.setattr(gateway_main, "_run_teaching_pack_worker", record_worker)
    monkeypatch.setenv("OMC_ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

    import packages.agents.checkpointer as checkpointer_module
    import packages.agents.teaching_pack.graph as teaching_pack_graph_module
    import services.gateway.teaching_pack_runtime as teaching_pack_runtime_module

    monkeypatch.setattr(teaching_pack_runtime_module, "create_async_engine", lambda url, pool_pre_ping: _FakeEngine())
    monkeypatch.setattr(teaching_pack_runtime_module, "async_sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(checkpointer_module, "get_checkpointer", _fake_get_checkpointer)
    monkeypatch.setattr(teaching_pack_graph_module, "build_teaching_pack_graph", lambda **kwargs: object())

    app = FastAPI()
    async with gateway_main.lifespan(app):
        assert not hasattr(app.state, "graph")
