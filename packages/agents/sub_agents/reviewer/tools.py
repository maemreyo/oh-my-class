from __future__ import annotations

from packages.agents.tools.capabilities import bind_agent_tools
from packages.agents.tools.fs import read_file as sandboxed_read_file


async def read_file(path: str) -> str:
    bind_agent_tools("reviewer", ("read_file",))
    return await sandboxed_read_file(path)
