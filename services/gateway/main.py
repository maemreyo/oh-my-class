"""FastAPI Gateway — entry point for oh-my-class pipeline.

Embeds LangGraph runtime. Exposes REST + WebSocket (SSE) for the teacher dashboard.
Port: 8001
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_config import configure_logging
from .middleware.auth_middleware import JWTMiddleware
from .middleware.error_handler import register_exception_handlers
from .middleware.request_id import RequestIDMiddleware
from .routers import approvals, artifacts, auth_router, runs, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize checkpointer, LLM clients."""
    import os

    configure_logging(log_level="INFO", json_output=True)

    from packages.agents.checkpointer import get_checkpointer

    environment = os.getenv("OMC_ENVIRONMENT", "development")
    app.state.checkpointer = get_checkpointer(environment)
    app.state.runs: dict = {}

    yield

    app.state.runs.clear()


app = FastAPI(
    title="oh-my-class Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(JWTMiddleware)
app.add_middleware(RequestIDMiddleware)

app.include_router(auth_router.router)
app.include_router(runs.router, prefix="/run", tags=["runs"])
app.include_router(artifacts.router, prefix="/run", tags=["artifacts"])
app.include_router(approvals.router, prefix="/run", tags=["approvals"])
app.include_router(webhooks.router, prefix="/webhook", tags=["webhooks"])


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok", "service": "oh-my-class-gateway"}
