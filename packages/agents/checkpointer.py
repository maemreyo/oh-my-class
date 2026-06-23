"""Checkpointer factory for LangGraph state persistence.

Provides the appropriate checkpointer based on deployment environment.
Development uses in-memory, staging uses SQLite, production uses PostgreSQL.
"""

from __future__ import annotations

from typing import Any

# Map of environment → checkpointer factory path
_CHECKPOINTER_MAP: dict[str, str] = {
    "development": "langgraph.checkpoint.memory.MemorySaver",
    "staging": "langgraph.checkpoint.sqlite.SqliteSaver",
    "production": "langgraph.checkpoint.postgres.PostgresSaver",
}


def get_checkpointer(environment: str = "development", **kwargs: Any) -> Any:
    """Create a checkpointer appropriate for the given environment.

    Args:
        environment: One of 'development', 'staging', 'production'.
        **kwargs: Additional arguments passed to the checkpointer constructor.
            For staging: db_path (default: 'omc_checkpoints.db').
            For production: connection_string (required).

    Returns:
        A LangGraph checkpointer instance.

    Raises:
        ValueError: If environment is not recognized.
        ImportError: If the required checkpointer package is not installed.
    """
    if environment not in _CHECKPOINTER_MAP:
        raise ValueError(
            f"Unknown environment '{environment}'. "
            f"Must be one of: {', '.join(_CHECKPOINTER_MAP)}"
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
    elif environment == "production":
        connection_string = kwargs.get("connection_string")
        if not connection_string:
            raise ValueError("connection_string required for production environment")
        return cls.from_conn_string(connection_string)

    return cls(**kwargs)
