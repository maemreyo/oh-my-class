"""Web search tool — stub implementation.

Provides web search capability for agents that need to gather external information.
Used by: Planner Agent (research_policy), Researcher Agent (all policies).
"""

from __future__ import annotations

from typing import Any


async def web_search(
    query: str,
    num_results: int = 5,
    *,
    min_sources: int = 2,
) -> list[dict[str, Any]]:
    """Search the web and return structured results.

    Args:
        query: Search query string.
        num_results: Maximum number of results to return.
        min_sources: Minimum number of independent sources required.

    Returns:
        List of search results, each containing 'title', 'url', 'snippet'.
    """
    # TODO: Implement via web_search provider (Exa, SerpAPI, etc.)
    raise NotImplementedError("web_search stub — implement with search provider")
