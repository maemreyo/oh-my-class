from __future__ import annotations

from packages.agents.tools.fs import read_file as sandboxed_read_file


async def read_file(
    path: str,
    encoding: str = "utf-8",
) -> str:
    return await sandboxed_read_file(path, encoding=encoding)
