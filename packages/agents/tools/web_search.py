"""Web search tool — stub implementation.

Provides web search capability for agents that need to gather external information.
Used by: Planner Agent (research_policy), Researcher Agent (all policies).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

_SOURCE_CATALOG = [
    ("Britannica Kids", "https://kids.britannica.com/search?query={query}"),
    ("National Geographic Education", "https://education.nationalgeographic.org/search/?q={query}"),
    ("Khan Academy", "https://www.khanacademy.org/search?page_search_query={query}"),
    ("NASA Climate Kids", "https://climatekids.nasa.gov/search/?q={query}"),
    ("Smithsonian Learning Lab", "https://learninglab.si.edu/search?st={query}"),
]


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
    encoded_query = quote_plus(query)
    limit = max(num_results, min_sources)
    return [
        {
            "title": title,
            "url": template.format(query=encoded_query),
            "snippet": f"Search this education source for classroom-safe material about {query}.",
            "verification_status": "UNCERTAIN",
        }
        for title, template in _SOURCE_CATALOG[:limit]
    ]
