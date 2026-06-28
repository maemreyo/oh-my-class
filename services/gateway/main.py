"""FastAPI Gateway — entry point for oh-my-class pipeline.

Embeds LangGraph runtime. Exposes REST + WebSocket (SSE) for the teacher dashboard.
Port: 8001
"""

from contextlib import asynccontextmanager

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
    notifications,
    teaching_pack_previews,
    teaching_pack_runs,
    release_evidence,
    runs,
    snapshots,
    webhooks,
)


async def _run_teaching_pack_sweeper(app: FastAPI) -> None:
    while True:
        await anyio.sleep(60)
        async with app.state.teaching_pack_session_factory() as session:
            from .recovery_sweeper import sweep_escalated_gates, sweep_stuck_jobs

            await sweep_stuck_jobs(session)
            await sweep_escalated_gates(session)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize checkpointer, graph, LLM clients."""
    import os

    configure_logging(log_level="INFO", json_output=True)

    from packages.agents.checkpointer import get_checkpointer
    from packages.agents.graph import build_oh_my_class_graph

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
    app.state.graph = build_oh_my_class_graph(
        environment=environment,
        checkpointer=app.state.checkpointer,
    )

    async with anyio.create_task_group() as task_group:
        task_group.start_soon(_run_teaching_pack_sweeper, app)
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3100"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JWTMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router.router)
app.include_router(runs.router, prefix="/run", tags=["runs"])
app.include_router(artifacts.router, prefix="/run", tags=["artifacts"])
app.include_router(snapshots.router, prefix="/run", tags=["snapshots"])
app.include_router(approvals.router, prefix="/run", tags=["approvals"])
app.include_router(teaching_pack_runs.router, prefix="/teaching-packs", tags=["teaching-pack"])
app.include_router(teaching_pack_previews.router, prefix="/teaching-packs", tags=["teaching-pack"])
app.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
app.include_router(release_evidence.router, prefix="/teaching-packs", tags=["release-evidence"])


@app.get("/health")  # pyright: ignore[reportUntypedFunctionDecorator]
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok", "service": "oh-my-class-gateway"}
