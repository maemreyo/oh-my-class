"""Real-DB tests for the checkpointer factory (no mocks for the production path).

#123 (OPS-10) surfaced a live bug here while investigating checkpoint-resume
semantics: `get_checkpointer("production", ...)` built a *sync* `PostgresSaver`
without ever entering its context manager (so it returned an unusable
`_GeneratorContextManager`, not a checkpointer), and even a correctly-entered
sync `PostgresSaver` cannot serve the teaching-pack graph, whose nodes are
`async def` and are invoked via `ainvoke`/`astream` -- `PostgresSaver`'s async
methods (`aget_tuple`, `aput`, ...) are unimplemented stubs that raise
`NotImplementedError`. This was previously untested and unused in the real
startup path (`services/gateway/main.py` never passed a `connection_string`),
so it would have crashed on first production startup.
"""

from __future__ import annotations

from contextlib import AsyncExitStack

import pytest

from packages.agents.checkpointer import get_checkpointer

DATABASE_URL = "postgresql://omc_dev:omc_dev@localhost:5432/oh_my_class"


class TestGetCheckpointer:
    async def test_development_returns_memory_saver(self) -> None:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = await get_checkpointer("development")

        assert isinstance(checkpointer, MemorySaver)

    async def test_unknown_environment_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown environment"):
            await get_checkpointer("nonexistent")

    async def test_production_without_connection_string_raises(self) -> None:
        async with AsyncExitStack() as stack:
            with pytest.raises(ValueError, match="connection_string required"):
                await get_checkpointer("production", exit_stack=stack)

    async def test_production_without_exit_stack_raises(self) -> None:
        with pytest.raises(ValueError, match="exit_stack required"):
            await get_checkpointer("production", connection_string=DATABASE_URL)

    async def test_production_returns_a_working_async_postgres_saver(self) -> None:
        """The regression check: a real graph node re-entering `ainvoke`
        against this checkpointer must not hit `NotImplementedError`."""
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncExitStack() as stack:
            checkpointer = await get_checkpointer(
                "production", exit_stack=stack, connection_string=DATABASE_URL,
            )

            assert isinstance(checkpointer, AsyncPostgresSaver)
            # Proves the async methods actually work (not NotImplementedError stubs).
            result = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": "checkpointer-factory-smoke-test"}},
            )
            assert result is None  # no checkpoint written yet -- just proving it doesn't raise
