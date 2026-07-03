from __future__ import annotations

from packages.agents.tools.fs import read_file as sandboxed_read_file
from packages.agents.tools.fs import write_file as sandboxed_write_file


async def read_file(path: str) -> str:
    return await sandboxed_read_file(path)


async def write_file(path: str, content: str, *, overwrite: bool = False) -> bool:
    return await sandboxed_write_file(path, content, overwrite=overwrite)
