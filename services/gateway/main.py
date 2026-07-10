from __future__ import annotations

"""FastAPI Gateway — entry point for oh-my-class pipeline.

Embeds LangGraph runtime. Exposes REST + WebSocket (SSE) for the teacher dashboard.
Port: 8001
"""

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anyio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .logging_config import configure_logging
from .middleware.auth_middleware import JWTMiddleware
from .middleware.error_handler import register_exception_handlers
from .middleware.request_id import RequestIDMiddleware
from .routers import (
    approvals,
    artifacts,
    auth_router,
    exports,
    media_assets,
    notifications,
    ops,
    release_evidence,
    runs,
    snapshots,
    teaching_pack_previews,
    teaching_pack_runs,
    teaching_session_live,
    unit_runs,
    webhooks,
)
from .secrets_guard import validate_production_secrets

if TYPE_CHECKING:
    from anyio.abc import TaskGroup
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class WorkerRuntimeConfig:
    mode: str
    concurrency: int


MAX_WORKER_CONCURRENCY = 10


def _quality_gate_enabled() -> bool:
    return os.getenv("OMC_ENABLE_SIX_LAYER_QUALITY", "true").casefold() in {"1", "true", "yes", "on"}


def _worker_runtime_config() -> WorkerRuntimeConfig:
    mode = os.getenv("WORKER_MODE", "in_process")
    raw_concurrency = os.getenv("WORKER_CONCURRENCY", "1")
    try:
        concurrency = int(raw_concurrency)
    except ValueError:
        concurrency = 1
    return WorkerRuntimeConfig(
        mode=mode,
        concurrency=min(max(concurrency, 1), MAX_WORKER_CONCURRENCY),
    )


async def _run_teaching_pack_sweeper(app: FastAPI) -> None:
    while True:
        await anyio.sleep(60)
        async with app.state.teaching_pack_session_factory() as session:
            from .recovery_sweeper import sweep_escalated_gates, sweep_stuck_jobs
            from .unit_orchestrator import reconcile_units

            await sweep_stuck_jobs(session)
            await sweep_escalated_gates(session)
            await reconcile_units(session)
            await session.commit()


async def _run_teaching_pack_worker(app: FastAPI, task_group: TaskGroup) -> None:
    from .outcome_delivery import SqlAlchemyOutcomeDeliverySink
    from .teaching_pack_completion import TeachingPackCompletionRecorder
    from .teaching_pack_executor import (
        TeachingPackExecutor,
        TeachingPackFailureRecorder,
    )
    from .teaching_pack_executor_types import InAppTeachingPackNotificationSink
    from .teaching_pack_export_store import TeachingPackExportStore
    from .teaching_pack_store import TeachingPackRunStore
    from .teaching_pack_worker import TeachingPackWorkerConfig, run_worker_batch

    def executor_factory(session: AsyncSession) -> TeachingPackExecutor:
        run_store = TeachingPackRunStore(session)
        notification_sink = InAppTeachingPackNotificationSink(session)
        return TeachingPackExecutor(
            app.state.teaching_pack_graph,
            _AnyioTeachingPackTaskGroup(task_group),
            TeachingPackFailureRecorder(run_store, notification_sink),
            TeachingPackCompletionRecorder(
                run_store,
                notifications=notification_sink,
                outcome_delivery=SqlAlchemyOutcomeDeliverySink(
                    app.state.teaching_pack_session_factory,
                ),
                export_store=TeachingPackExportStore(session),
            ),
        )

    runtime = _worker_runtime_config()
    config = TeachingPackWorkerConfig(
        worker_id="gateway-worker",
        lease_seconds=120,
        idle_sleep_seconds=1.0,
        worker_concurrency=runtime.concurrency,
    )

    while True:
        claimed = await run_worker_batch(
            app.state.teaching_pack_session_factory,
            executor_factory,
            config,
        )
        if claimed == 0:
            await anyio.sleep(config.idle_sleep_seconds)


class _AnyioTeachingPackTaskGroup:
    def __init__(self, task_group: TaskGroup) -> None:
        self._task_group = task_group

    def start_soon(self, func, *args) -> None:
        self._task_group.start_soon(func, *args)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize checkpointer, store, graph, LLM clients."""
    import contextlib

    configure_logging(log_level="INFO", json_output=True)
    validate_production_secrets()

    from packages.agents.checkpointer import get_checkpointer
    from packages.agents.teaching_pack.graph import build_teaching_pack_graph
    from packages.agents.teaching_pack.store import (
        get_development_store,
        open_teaching_pack_store,
        sync_connection_string,
    )
    from services.gateway.teaching_pack_quality_gate import GatewayTeachingPackQualityGate

    environment = os.getenv("OMC_ENVIRONMENT", "development")
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class",
    )
    app.state.teaching_pack_engine = create_async_engine(database_url, pool_pre_ping=True)
    app.state.teaching_pack_session_factory = async_sessionmaker(
        app.state.teaching_pack_engine,
        expire_on_commit=False,
    )
    app.state.checkpointer = get_checkpointer(environment)
    app.state.runs = {}

    with contextlib.ExitStack() as stack:
        if environment in ("staging", "production"):
            store = stack.enter_context(
                open_teaching_pack_store(sync_connection_string(database_url))
            )
        else:
            store = get_development_store()

        app.state.store = store
        app.state.teaching_pack_graph = build_teaching_pack_graph(
            checkpointer=app.state.checkpointer,
            store=store,
            quality_gate=GatewayTeachingPackQualityGate() if _quality_gate_enabled() else None,
        )

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(_run_teaching_pack_sweeper, app)
            runtime = _worker_runtime_config()
            if runtime.mode == "in_process":
                task_group.start_soon(_run_teaching_pack_worker, app, task_group)
            try:
                yield
            finally:
                task_group.cancel_scope.cancel()

    await app.state.teaching_pack_engine.dispose()
    app.state.runs.clear()


app = FastAPI(
    title="oh-my-class Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(JWTMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(runs.router, prefix="/run", tags=["runs"])
app.include_router(artifacts.router, prefix="/run", tags=["artifacts"])
app.include_router(snapshots.router, prefix="/run", tags=["snapshots"])
app.include_router(approvals.router, prefix="/run", tags=["approvals"])
app.include_router(teaching_pack_runs.router, prefix="/teaching-packs", tags=["teaching-pack"])
app.include_router(teaching_pack_previews.router, prefix="/teaching-packs", tags=["teaching-pack"])
app.include_router(exports.router, prefix="/teaching-packs", tags=["exports"])
app.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(ops.router)
app.include_router(release_evidence.router, prefix="/teaching-packs", tags=["release-evidence"])
app.include_router(unit_runs.router, prefix="/teaching-packs", tags=["units"])
app.include_router(media_assets.router)
app.include_router(
    teaching_session_live.router, prefix="/teaching-sessions", tags=["teaching-session"],
)


@app.get("/health")  # pyright: ignore[reportUntypedFunctionDecorator]
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok", "service": "oh-my-class-gateway"}
