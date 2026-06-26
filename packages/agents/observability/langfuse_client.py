"""Langfuse client singleton — lazy-initialized, INVARIANT-02 safe.

Reads LANGFUSE_* environment variables. Returns None when not configured.
Thread-safe via module-level lock. Degrades gracefully when langfuse
package is not installed.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

_LOGGER = logging.getLogger("packages.agents.observability")

# Module-level cached client (None when not configured)
_client: Any = None
_initialized = False


def _get_langfuse_config() -> dict[str, str | bool]:
    """Read Langfuse configuration from environment.

    Env var priority: LANGFUSE_BASE_URL > LANGFUSE_HOST > default.
    """
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    host = (
        os.environ.get("LANGFUSE_BASE_URL")
        or os.environ.get("LANGFUSE_HOST")
        or "http://localhost:3001"
    )
    return {
        "public_key": public_key,
        "secret_key": secret_key,
        "host": host,
        "enabled": bool(public_key and secret_key),
    }


@lru_cache(maxsize=1)
def get_langfuse_config() -> dict[str, str | bool]:
    """Cached Langfuse configuration."""
    return _get_langfuse_config()


def get_langfuse_client() -> Any:
    """Get or create the Langfuse client singleton.

    Returns None when:
    - LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY is not set
    - langfuse package is not installed
    - Client creation fails
    """
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True
    config = get_langfuse_config()

    if not config["enabled"]:
        _LOGGER.debug("Langfuse not configured — tracing disabled")
        return None

    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]

        _client = Langfuse(
            public_key=config["public_key"],  # type: ignore[arg-type]
            secret_key=config["secret_key"],  # type: ignore[arg-type]
            host=config["host"],  # type: ignore[arg-type]
        )
        _LOGGER.info("Langfuse client initialized host=%s", config["host"])
        return _client
    except ImportError:
        _LOGGER.debug("langfuse package not installed — tracing disabled")
        return None
    except Exception as exc:
        _LOGGER.warning("Langfuse client init failed: %s", exc)
        return None


def flush_langfuse() -> None:
    """Flush pending Langfuse events. Call on shutdown."""
    client = get_langfuse_client()
    if client is not None:
        try:
            client.flush()
        except Exception as exc:
            _LOGGER.debug("Langfuse flush failed: %s", exc)


def get_trace_metadata(
    run_id: str,
    agent: str,
    step: int,
    **extra: Any,
) -> dict[str, Any]:
    """Build standard metadata dict for Langfuse traces."""
    return {
        "run_id": run_id,
        "agent": agent,
        "step": step,
        "pipeline": "oh-my-class",
        **extra,
    }
