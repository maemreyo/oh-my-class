from __future__ import annotations

from typing import Any

from packages.agents.tools.fs import read_file as sandboxed_read_file
from packages.agents.tools.ninerouter_web import NineRouterFetchRequest, NineRouterWebClient
from packages.agents.tools.web_search import web_search as shared_web_search


async def web_search(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    return await shared_web_search(query, num_results=num_results)


async def web_fetch(url: str, *, extract_text: bool = True) -> str:
    client = NineRouterWebClient()
    result = await client.fetch(NineRouterFetchRequest(url=url, format="markdown"))
    return result.content if extract_text else result.model_dump_json()


async def read_file(path: str) -> str:
    return await sandboxed_read_file(path)
