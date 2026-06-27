from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from packages.agents.tools.ninerouter_web import FetchResult as RouterFetchResult
from packages.agents.tools.ninerouter_web import SearchResult
from services.gateway.research_collector import FetchUnavailableError
from services.gateway.research_provider_9router import NineRouterResearchProviders


class TestNineRouterResearchProviders:
    @pytest.mark.anyio
    async def test_maps_search_results_to_research_candidates(self) -> None:
        providers = NineRouterResearchProviders(FakeNineRouterClient(), max_results=3)

        results = await providers.search("fractions")

        assert len(results) == 1
        assert results[0].title == "Fractions"
        assert results[0].url == "https://edu.test/fractions"
        assert results[0].snippet == "fraction source"

    @pytest.mark.anyio
    async def test_maps_fetch_result_to_source_evidence(self) -> None:
        providers = NineRouterResearchProviders(FakeNineRouterClient())

        result = await providers.fetch("source-1", "https://edu.test/fractions")

        assert result.source_id == "source-1"
        assert result.content == "Fetched markdown"

    @pytest.mark.anyio
    async def test_fetch_http_error_becomes_unavailable_source(self) -> None:
        providers = NineRouterResearchProviders(FailingFetchClient())

        with pytest.raises(FetchUnavailableError) as exc_info:
            await providers.fetch("source-1", "https://edu.test/fail")

        assert exc_info.value.url == "https://edu.test/fail"


@dataclass(frozen=True, slots=True)
class FakeNineRouterClient:
    async def search(self, request) -> list[SearchResult]:
        assert request.query == "fractions"
        assert request.max_results == 3
        return [
            SearchResult(
                title="Fractions",
                url="https://edu.test/fractions",
                snippet="fraction source",
            ),
        ]

    async def fetch(self, request) -> RouterFetchResult:
        assert request.url == "https://edu.test/fractions"
        return RouterFetchResult(url=request.url, content="Fetched markdown")


@dataclass(frozen=True, slots=True)
class FailingFetchClient:
    async def search(self, request) -> list[SearchResult]:
        return []

    async def fetch(self, request) -> RouterFetchResult:
        raise httpx.ConnectError("unreachable")
