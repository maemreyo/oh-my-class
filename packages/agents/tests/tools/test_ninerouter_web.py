from __future__ import annotations

from typing import Any

import httpx
import pytest

from packages.agents.tools.ninerouter_web import (
    NineRouterFetchRequest,
    NineRouterSearchRequest,
    NineRouterWebClient,
)
from packages.agents.tools.web_search import web_search


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "http://test.local")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("failed", request=request, response=response)

    def json(self) -> dict[str, Any]:
        return self._payload


class FakeAsyncClient:
    calls: list[dict[str, Any]] = []
    response = FakeResponse({})

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> FakeResponse:
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": self.timeout})
        return self.response


@pytest.fixture(autouse=True)
def reset_fake_client(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse({})
    monkeypatch.setattr("packages.agents.tools.ninerouter_web.httpx.AsyncClient", FakeAsyncClient)


@pytest.mark.asyncio
async def test_search_posts_to_ninerouter_search_endpoint() -> None:
    FakeAsyncClient.response = FakeResponse({
        "results": [
            {
                "title": "Equivalent fractions",
                "url": "https://example.edu/fractions",
                "snippet": "Classroom explanation",
                "source": "example.edu",
            },
        ],
    })
    client = NineRouterWebClient(base_url="http://router.local/v1", api_key="test-key")

    results = await client.search(NineRouterSearchRequest(query="fractions", max_results=3))

    assert len(results) == 1
    assert results[0].title == "Equivalent fractions"
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://router.local/v1/search"
    assert call["json"]["model"] == "4omc.search"
    assert call["json"]["search_type"] == "web"
    assert call["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_search_http_error_returns_empty_results() -> None:
    FakeAsyncClient.response = FakeResponse({}, status_code=500)
    client = NineRouterWebClient(base_url="http://router.local/v1", api_key="")

    results = await client.search(NineRouterSearchRequest(query="fractions"))

    assert results == []


@pytest.mark.asyncio
async def test_fetch_returns_markdown_content() -> None:
    FakeAsyncClient.response = FakeResponse({
        "title": "Example",
        "content": "# Equivalent fractions\nTwo fractions can name the same amount.",
    })
    client = NineRouterWebClient(base_url="http://router.local/v1", api_key="")

    result = await client.fetch(NineRouterFetchRequest(url="https://example.edu/fractions"))

    assert result.title == "Example"
    assert "Equivalent fractions" in result.content
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "http://router.local/v1/web/fetch"
    assert call["json"]["model"] == "4omc.fetch"
    assert "Authorization" not in call["headers"]


@pytest.mark.asyncio
async def test_fetch_handles_dict_content_format() -> None:
    FakeAsyncClient.response = FakeResponse({
        "provider": "exa",
        "title": "Example",
        "content": {
            "format": "markdown",
            "text": "# Equivalent fractions\nTwo fractions can name the same amount.",
            "length": 4330,
        },
        "metrics": {"response_time_ms": 276},
    })
    client = NineRouterWebClient(base_url="http://router.local/v1", api_key="")

    result = await client.fetch(NineRouterFetchRequest(url="https://example.edu/fractions"))

    assert result.title == "Example"
    assert "Equivalent fractions" in result.content


@pytest.mark.asyncio
async def test_fetch_without_content_raises_value_error() -> None:
    FakeAsyncClient.response = FakeResponse({"title": "Missing content"})
    client = NineRouterWebClient(base_url="http://router.local/v1", api_key="")

    with pytest.raises(ValueError, match="no markdown content"):
        await client.fetch(NineRouterFetchRequest(url="https://example.edu/fractions"))


@pytest.mark.asyncio
async def test_web_search_maps_results_to_uncertain_sources() -> None:
    FakeAsyncClient.response = FakeResponse({
        "results": [
            {"title": "A", "url": "https://a.example", "snippet": "Alpha"},
            {"title": "B", "url": "https://b.example", "snippet": "Beta"},
        ],
    })

    results = await web_search("fractions", num_results=1, min_sources=2)

    assert len(results) == 2
    assert all(result["verification_status"] == "UNCERTAIN" for result in results)
