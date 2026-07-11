"""Checkpointer factory for LangGraph state persistence.

Provides the appropriate checkpointer based on deployment environment.
Development uses in-memory, staging uses SQLite, production uses PostgreSQL.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from contextlib import AsyncExitStack

# Map of environment → checkpointer factory path (production is handled
# separately below -- it needs the async variant, not this sync one).
_CHECKPOINTER_MAP: dict[str, str] = {
    "development": "langgraph.checkpoint.memory.MemorySaver",
    "staging": "langgraph.checkpoint.sqlite.SqliteSaver",
}


async def get_checkpointer(
    environment: str = "development", *, exit_stack: AsyncExitStack | None = None, **kwargs: Any,
) -> Any:
    """Create a checkpointer appropriate for the given environment.

    Args:
        environment: One of 'development', 'staging', 'production'.
        exit_stack: Required for 'production' -- an `AsyncExitStack` owned by
            the caller (e.g. the app lifespan) that keeps the underlying
            connection open for the checkpointer's lifetime and closes it on
            shutdown.
        **kwargs: Additional arguments passed to the checkpointer constructor.
            For staging: db_path (default: 'omc_checkpoints.db').
            For production: connection_string (required; a psycopg-style
            `postgresql://...` DSN, not `+asyncpg`).

    Returns:
        A LangGraph checkpointer instance, ready to use (already `.setup()`
        for production).

    Raises:
        ValueError: If environment is not recognized, or a required argument
            is missing.
        ImportError: If the required checkpointer package is not installed.
    """
    if environment == "production":
        # Teaching-pack graph nodes are `async def` and the graph is invoked
        # via `ainvoke`/`astream` (services/gateway/teaching_pack_executor.py).
        # The sync `PostgresSaver`'s async methods (`aget_tuple`, `aput`, ...)
        # are unimplemented stubs that raise `NotImplementedError` -- only
        # `AsyncPostgresSaver` actually works against an async graph.
        connection_string = kwargs.get("connection_string")
        if not connection_string:
            raise ValueError("connection_string required for production environment")
        if exit_stack is None:
            raise ValueError("exit_stack required for production environment")

        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = await exit_stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(connection_string),
        )
        await checkpointer.setup()
        return checkpointer

    if environment not in _CHECKPOINTER_MAP:
        raise ValueError(
            f"Unknown environment '{environment}'. "
            f"Must be one of: {', '.join((*_CHECKPOINTER_MAP, 'production'))}"
        )

    import importlib

    module_path = _CHECKPOINTER_MAP[environment]
    module_name, class_name = module_path.rsplit(".", 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        raise ImportError(
            f"Cannot import {module_name}. "
            f"Install the required package for '{environment}' environment."
        ) from e

    cls = getattr(module, class_name)

    if environment == "development":
        return cls()
    elif environment == "staging":
        db_path = kwargs.get("db_path", "omc_checkpoints.db")
        return cls(db_path=db_path)

    return cls(**kwargs)
