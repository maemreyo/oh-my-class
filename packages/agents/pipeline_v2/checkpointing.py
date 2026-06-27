from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator


class PipelineV2Checkpointer(Protocol):
    def setup(self) -> None: ...


@contextmanager
def open_pipeline_v2_postgres_checkpointer(
    connection_string: str,
    *,
    setup: bool = True,
) -> Iterator[PipelineV2Checkpointer]:
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(connection_string) as checkpointer:
        if setup:
            checkpointer.setup()
        yield checkpointer
