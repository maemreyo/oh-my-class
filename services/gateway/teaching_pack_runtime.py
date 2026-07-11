"""Shared builder for the teaching-pack graph/checkpointer/store runtime.

#119 (OPS-06)'s own implementation notes call for exactly this: "Factor the
executor/graph construction out of `lifespan` into a shared builder so API
and worker use one code path (avoids drift)." Extracted from
`main.py`'s `lifespan()` so the in-process worker (API process) and the
standalone worker entrypoint (`worker_entrypoint.py`) build the identical
graph/checkpointer/store instead of two independently-maintained code paths
that could silently diverge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from contextlib import AsyncExitStack

    from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker as AsyncSessionFactory


@dataclass(slots=True)
class TeachingPackRuntime:
    """Everything the API process and a standalone worker process both need
    to run teaching-pack jobs, built exactly once per process via
    `build_teaching_pack_runtime`."""

    environment: str
    engine: AsyncEngine
    session_factory: AsyncSessionFactory
    checkpointer: Any
    store: Any
    export_writer: Any
    graph: Any


def quality_gate_enabled() -> bool:
    return os.getenv("OMC_ENABLE_SIX_LAYER_QUALITY", "true").casefold() in {"1", "true", "yes", "on"}


async def build_teaching_pack_runtime(
    *, environment: str, database_url: str, exit_stack: AsyncExitStack,
) -> TeachingPackRuntime:
    """Build the engine, checkpointer, store, export writer, and compiled
    graph for one process. `exit_stack` owns the lifetime of anything that
    needs async cleanup (the production `AsyncPostgresSaver` connection,
    the sync store's connection) -- the caller (API lifespan or worker
    entrypoint) is responsible for entering/exiting it around the process's
    actual running lifetime.
    """
    from packages.agents.checkpointer import get_checkpointer
    from packages.agents.teaching_pack.graph import build_teaching_pack_graph
    from packages.agents.teaching_pack.store import (
        get_development_store,
        open_teaching_pack_store,
        sync_connection_string,
    )
    from services.gateway.artifact_document_content_store import GatewayArtifactDocumentContentStore
    from services.gateway.teaching_pack_export_writer import export_writer_for_environment
    from services.gateway.teaching_pack_quality_gate import GatewayTeachingPackQualityGate

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    if environment in ("staging", "production"):
        store = exit_stack.enter_context(
            open_teaching_pack_store(sync_connection_string(database_url)),
        )
    else:
        store = get_development_store()

    checkpointer = await get_checkpointer(
        environment,
        exit_stack=exit_stack,
        connection_string=sync_connection_string(database_url),
    )
    export_writer = export_writer_for_environment(environment)
    content_store = GatewayArtifactDocumentContentStore(session_factory)
    graph = build_teaching_pack_graph(
        checkpointer=checkpointer,
        store=store,
        quality_gate=GatewayTeachingPackQualityGate() if quality_gate_enabled() else None,
        content_store=content_store,
    )

    return TeachingPackRuntime(
        environment=environment,
        engine=engine,
        session_factory=session_factory,
        checkpointer=checkpointer,
        store=store,
        export_writer=export_writer,
        graph=graph,
    )
