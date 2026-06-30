from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from langgraph.store.base import BaseStore


@contextmanager
def open_teaching_pack_store(
    connection_string: str,
    *,
    setup: bool = True,
    sweep_interval_minutes: int = 60,
) -> Iterator[BaseStore]:
    """Open a PostgresStore for cross-run memory on the same Postgres as the checkpointer.

    Additive to the checkpointer (thread state ≠ cross-run memory).
    Configures TTL sweeper for research-cache recency. Stops sweeper on exit.

    Args:
        connection_string: psycopg3-style URL (postgresql://user:pass@host/db).
            Strip '+asyncpg' from the SQLAlchemy DATABASE_URL if sharing env vars.
        setup: Run store.setup() to create tables on first open.
        sweep_interval_minutes: How often the TTL sweeper deletes expired entries.
    """
    from langgraph.store.postgres import PostgresStore
    from langgraph.store.postgres.base import TTLConfig

    ttl: TTLConfig = {
        "refresh_on_read": True,
        "sweep_interval_minutes": sweep_interval_minutes,
    }
    with PostgresStore.from_conn_string(connection_string, ttl=ttl) as store:
        if setup:
            store.setup()
        store.start_ttl_sweeper()
        try:
            yield store
        finally:
            store.stop_ttl_sweeper()


def get_development_store() -> BaseStore:
    """Return an InMemoryStore for development and test environments."""
    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def sync_connection_string(database_url: str) -> str:
    """Convert an asyncpg SQLAlchemy URL to a psycopg3-compatible URL.

    PostgresStore uses psycopg3 (sync), not asyncpg. Strip the '+asyncpg'
    driver suffix from DATABASE_URL before passing to open_teaching_pack_store.
    """
    return database_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres+asyncpg://", "postgresql://"
    )
