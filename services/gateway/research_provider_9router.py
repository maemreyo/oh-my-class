from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import httpx

from packages.agents.tools.ninerouter_web import NineRouterFetchRequest, NineRouterSearchRequest
from services.gateway.research_collector import FetchUnavailableError
from services.gateway.research_engine import FetchResult, SearchCandidate

if TYPE_CHECKING:
    from packages.agents.tools.ninerouter_web import FetchResult as RouterFetchResult
    from packages.agents.tools.ninerouter_web import SearchResult


class NineRouterSearchFetchClient(Protocol):
    async def search(self, request: NineRouterSearchRequest) -> list[SearchResult]: ...

    async def fetch(self, request: NineRouterFetchRequest) -> RouterFetchResult: ...


@dataclass(frozen=True, slots=True)
class NineRouterResearchProviders:
    client: NineRouterSearchFetchClient
    max_results: int = 5

    async def search(self, query: str) -> tuple[SearchCandidate, ...]:
        results = await self.client.search(NineRouterSearchRequest(
            query=query,
            max_results=self.max_results,
        ))
        return tuple(
            SearchCandidate(title=result.title, url=result.url, snippet=result.snippet)
            for result in results
        )

    async def fetch(self, source_id: str, url: str) -> FetchResult:
        try:
            result = await self.client.fetch(NineRouterFetchRequest(url=url, format="markdown"))
        except (httpx.HTTPError, ValueError) as error:
            raise FetchUnavailableError(url) from error
        return FetchResult(source_id=source_id, content=result.content)
