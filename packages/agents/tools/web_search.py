from __future__ import annotations

from typing import Any

from packages.agents.tools.ninerouter_web import NineRouterSearchRequest, NineRouterWebClient


async def web_search(
    query: str,
    num_results: int = 5,
    *,
    min_sources: int = 2,
) -> list[dict[str, Any]]:
    limit = max(num_results, min_sources)
    client = NineRouterWebClient()
    results = await client.search(NineRouterSearchRequest(query=query, max_results=limit))
    return [
        {
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "verification_status": "UNCERTAIN",
        }
        for result in results[:limit]
    ]
