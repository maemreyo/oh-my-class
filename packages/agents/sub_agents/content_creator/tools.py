from __future__ import annotations

from packages.agents.tools.capabilities import bind_agent_tools
from packages.agents.tools.fs import read_file as sandboxed_read_file
from packages.agents.tools.fs import write_file as sandboxed_write_file


async def read_file(path: str) -> str:
    bind_agent_tools("content_creator", ("read_file",))
    return await sandboxed_read_file(path)


async def write_file(path: str, content: str, *, overwrite: bool = False) -> bool:
    bind_agent_tools("content_creator", ("write_file",))
    return await sandboxed_write_file(path, content, overwrite=overwrite)
