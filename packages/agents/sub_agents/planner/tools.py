from __future__ import annotations

from typing import Any

from packages.agents.tools.web_search import web_search as shared_web_search


async def web_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    return await shared_web_search(query, num_results=num_results)


async def read_file(path: str) -> str:
    """Read a file from the workspace (curriculum standards, templates, etc.).

    Args:
        path: File path to read.

    Returns:
        File contents as string.
    """
    # TODO: Delegate to packages.agents.tools.read_file
    raise NotImplementedError("planner read_file stub")
