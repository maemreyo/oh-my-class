from __future__ import annotations

from typing import Any

from packages.agents.tools.capabilities import bind_agent_tools
from packages.agents.tools.fs import read_file as sandboxed_read_file
from packages.agents.tools.web_search import web_search as shared_web_search


async def web_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    bind_agent_tools("planner", ("web_search",))
    return await shared_web_search(query, num_results=num_results)


async def read_file(path: str) -> str:
    bind_agent_tools("planner", ("read_file",))
    return await sandboxed_read_file(path)
