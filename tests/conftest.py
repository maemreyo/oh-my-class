from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@dataclass(frozen=True, slots=True)
class RealLlmTestConfig:
    base_url: str
    model: str
    timeout_s: float


@dataclass(frozen=True, slots=True)
class DeepevalHarnessConfig:
    judge_base_url: str
    judge_model: str
    telemetry_disabled: bool
    langfuse_enabled: bool


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "real_llm: live 9Router-backed LLM tests excluded from per-commit fast tier",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    _ = config
    if os.getenv("OMC_RUN_REAL_LLM_TESTS", "").casefold() in {"1", "true", "yes", "on"}:
        return
    skip_real_llm = pytest.mark.skip(
        reason="set OMC_RUN_REAL_LLM_TESTS=1 to run live 9Router tests",
    )
    for item in items:
        if "real_llm" in item.keywords:
            item.add_marker(skip_real_llm)


@pytest.fixture
def real_llm_config() -> RealLlmTestConfig:
    return RealLlmTestConfig(
        base_url=os.getenv("OMC_TEST_9ROUTER_BASE_URL", "http://127.0.0.1:20228"),
        model=os.getenv("OMC_TEST_9ROUTER_MODEL", "4omc"),
        timeout_s=float(os.getenv("OMC_TEST_9ROUTER_TIMEOUT_S", "60")),
    )


@pytest.fixture
def deepeval_harness_config(real_llm_config: RealLlmTestConfig) -> DeepevalHarnessConfig:
    os.environ.setdefault("CONFIDENT_AI_DISABLE_TRACKING", "true")
    return DeepevalHarnessConfig(
        judge_base_url=real_llm_config.base_url,
        judge_model=real_llm_config.model,
        telemetry_disabled=os.environ["CONFIDENT_AI_DISABLE_TRACKING"].lower() == "true",
        langfuse_enabled=bool(
            os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
        ),
    )


@pytest.fixture
async def real_db_session() -> AsyncIterator[AsyncSession]:
    database_url = os.getenv(
        "OMC_TEST_DATABASE_URL",
        "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
    )
    engine = create_async_engine(database_url, pool_pre_ping=True)
    connection = await engine.connect()
    transaction = await connection.begin()
    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await transaction.rollback()
    await connection.close()
    await engine.dispose()
