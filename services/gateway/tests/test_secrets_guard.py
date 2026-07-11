from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from fastapi import FastAPI

from services.gateway import main as gateway_main
from services.gateway.secrets_guard import ProductionSecretsError, validate_production_secrets

if TYPE_CHECKING:
    from collections.abc import Callable


VALID_PRODUCTION_ENV = {
    "ENV": "production",
    "POSTGRES_PASSWORD": "postgres-prod-secret",
    "REDIS_AUTH": "redis-prod-secret",
    "LANGFUSE_ENCRYPTION_KEY": "langfuse-encryption-prod-secret",
    "LANGFUSE_NEXTAUTH_SECRET": "nextauth-prod-secret",
    "CLICKHOUSE_PASSWORD": "clickhouse-prod-secret",
    "MINIO_ROOT_PASSWORD": "minio-prod-secret",
}


class _FakeEngine:
    async def dispose(self) -> None:
        return None


class TestProductionSecretsGuard:
    def test_production_default_postgres_password_is_rejected(self) -> None:
        env = VALID_PRODUCTION_ENV | {"POSTGRES_PASSWORD": "omc_dev"}

        with pytest.raises(ProductionSecretsError) as exc_info:
            validate_production_secrets(env)

        assert exc_info.value.offenders == ("POSTGRES_PASSWORD",)
        assert "POSTGRES_PASSWORD" in str(exc_info.value)

    def test_production_all_zero_langfuse_encryption_key_is_rejected(self) -> None:
        env = VALID_PRODUCTION_ENV | {"LANGFUSE_ENCRYPTION_KEY": "0" * 64}

        with pytest.raises(ProductionSecretsError) as exc_info:
            validate_production_secrets(env)

        assert exc_info.value.offenders == ("LANGFUSE_ENCRYPTION_KEY",)

    def test_production_lists_every_offending_secret(self) -> None:
        env = VALID_PRODUCTION_ENV | {
            "POSTGRES_PASSWORD": "omc_dev",
            "REDIS_AUTH": "",
            "MINIO_ROOT_PASSWORD": "minioadmin",
        }

        with pytest.raises(ProductionSecretsError) as exc_info:
            validate_production_secrets(env)

        assert exc_info.value.offenders == ("POSTGRES_PASSWORD", "REDIS_AUTH", "MINIO_ROOT_PASSWORD")

    def test_development_allows_defaults(self) -> None:
        validate_production_secrets(
            {
                "ENV": "development",
                "POSTGRES_PASSWORD": "omc_dev",
                "REDIS_AUTH": "omc_redis_secret",
                "LANGFUSE_ENCRYPTION_KEY": "0" * 64,
            },
        )

    def test_lifespan_refuses_production_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        anyio.run(_assert_lifespan_refuses_production_defaults, monkeypatch)

    def test_lifespan_accepts_overridden_production_secrets(self, monkeypatch: pytest.MonkeyPatch) -> None:
        anyio.run(_assert_lifespan_accepts_production_secrets, monkeypatch)


async def _assert_lifespan_refuses_production_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_gateway_lifespan_dependencies(monkeypatch)
    _set_env(monkeypatch, VALID_PRODUCTION_ENV | {"POSTGRES_PASSWORD": "omc_dev"})

    with pytest.raises(ProductionSecretsError, match="POSTGRES_PASSWORD"):
        async with gateway_main.lifespan(FastAPI()):
            pass


async def _assert_lifespan_accepts_production_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_gateway_lifespan_dependencies(monkeypatch)
    _set_env(monkeypatch, VALID_PRODUCTION_ENV | {"WORKER_MODE": "external"})

    async with gateway_main.lifespan(FastAPI()) as _:
        pass


async def _fake_get_checkpointer(environment: str, **kwargs: object) -> object:
    _ = (environment, kwargs)
    return object()


def _set_gateway_lifespan_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_sessionmaker(engine: _FakeEngine, expire_on_commit: bool) -> Callable[[], object]:
        _ = (engine, expire_on_commit)
        return object

    monkeypatch.setattr(gateway_main, "configure_logging", lambda **kwargs: None)
    monkeypatch.setattr(gateway_main, "_run_teaching_pack_sweeper", _sleep_forever)

    import packages.agents.checkpointer as checkpointer_module
    import packages.agents.teaching_pack.graph as teaching_pack_graph_module
    import services.gateway.teaching_pack_runtime as teaching_pack_runtime_module

    monkeypatch.setattr(teaching_pack_runtime_module, "create_async_engine", lambda url, pool_pre_ping: _FakeEngine())
    monkeypatch.setattr(teaching_pack_runtime_module, "async_sessionmaker", fake_sessionmaker)
    monkeypatch.setattr(checkpointer_module, "get_checkpointer", _fake_get_checkpointer)
    monkeypatch.setattr(teaching_pack_graph_module, "build_teaching_pack_graph", lambda **kwargs: object())


async def _sleep_forever(*_args: object) -> None:
    await anyio.sleep_forever()


def _set_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)
