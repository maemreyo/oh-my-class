"""Planner Agent tools — web_search and read_file for research.

Tools available to the Planner Agent for gathering information
during lesson plan design.
"""

from __future__ import annotations

from typing import Any


async def web_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    """Search the web for curriculum and pedagogical references.

    Args:
        query: Search query for educational content.
        num_results: Maximum results to return.

    Returns:
        List of search results with title, url, snippet.
    """
    # TODO: Delegate to packages.agents.tools.web_search
    raise NotImplementedError("planner web_search stub")


async def read_file(path: str) -> str:
    """Read a file from the workspace (curriculum standards, templates, etc.).

    Args:
        path: File path to read.

    Returns:
        File contents as string.
    """
    # TODO: Delegate to packages.agents.tools.read_file
    raise NotImplementedError("planner read_file stub")
