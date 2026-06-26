from __future__ import annotations

import logging
import os
import time
from typing import Any, Final, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field

NINEROUTER_BASE_URL: Final = "http://localhost:20128/v1"
_LOGGER: Final = logging.getLogger("packages.agents.tools.ninerouter_web")


class NineRouterSearchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: Literal["f.pro.search"] = "f.pro.search"
    query: str = Field(min_length=1)
    search_type: Literal["web"] = "web"
    max_results: int = Field(default=5, ge=1, le=20)


class NineRouterFetchRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: Literal["f.pro.fetch"] = "f.pro.fetch"
    url: str = Field(min_length=1, max_length=2000)
    format: Literal["markdown"] = "markdown"


class SearchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str = Field(min_length=1)
    url: str = Field(min_length=1, max_length=2000)
    snippet: str = ""
    source: str | None = None


class FetchResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    url: str = Field(min_length=1, max_length=2000)
    content: str
    title: str | None = None
    format: Literal["markdown"] = "markdown"


class NineRouterWebClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        configured_base_url = base_url or os.environ.get("NINEROUTER_BASE_URL")
        self._base_url = (configured_base_url or NINEROUTER_BASE_URL).rstrip("/")
        self._api_key = api_key if api_key is not None else os.environ.get("NINEROUTER_API_KEY", "")

    async def search(self, request: NineRouterSearchRequest) -> list[SearchResult]:
        started = _log_web_start("search", request.model, query=request.query)
        try:
            payload = await self._post_json("/search", request.model_dump())
            results = _extract_result_items(payload)
            parsed = [_parse_search_result(item) for item in results]
            _log_web_success("search", request.model, started, result_count=len(parsed))
            return parsed[: request.max_results]
        except (httpx.HTTPError, ValueError) as error:
            _log_web_failure("search", request.model, started, error)
            return []

    async def fetch(self, request: NineRouterFetchRequest) -> FetchResult:
        started = _log_web_start("fetch", request.model, url=request.url)
        try:
            payload = await self._post_json("/web/fetch", request.model_dump())
            result = _parse_fetch_result(request.url, payload)
            _log_web_success(
                "fetch",
                request.model,
                started,
                content_chars=len(result.content),
            )
            return result
        except (httpx.HTTPError, ValueError) as error:
            _log_web_failure("fetch", request.model, started, error)
            raise

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}{path}", json=payload, headers=headers)
            response.raise_for_status()
        parsed = response.json()
        if not isinstance(parsed, dict):
            raise ValueError(f"9Router {path} returned non-object JSON")
        return parsed


def _extract_result_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = payload.get("results") or payload.get("data") or payload.get("items")
    if not isinstance(candidates, list):
        return []
    return [item for item in candidates if isinstance(item, dict)]


def _parse_search_result(item: dict[str, Any]) -> SearchResult:
    title = str(item.get("title") or item.get("name") or item.get("url") or "Untitled source")
    url = str(item.get("url") or item.get("link") or "")
    snippet = str(item.get("snippet") or item.get("description") or item.get("content") or "")
    source_value = item.get("source")
    source = str(source_value) if source_value is not None else None
    return SearchResult(title=title, url=url, snippet=snippet, source=source)


def _parse_fetch_result(url: str, payload: dict[str, Any]) -> FetchResult:
    content_value = payload.get("content") or payload.get("markdown") or payload.get("text")
    if not isinstance(content_value, str):
        data = payload.get("data")
        if isinstance(data, dict):
            content_value = data.get("content") or data.get("markdown") or data.get("text")
    if not isinstance(content_value, str):
        raise ValueError("9Router fetch returned no markdown content")
    title_value = payload.get("title")
    title = str(title_value) if title_value is not None else None
    return FetchResult(url=url, content=content_value, title=title)


def _log_web_start(call_type: str, model: str, **details: str) -> float:
    started = time.monotonic()
    _LOGGER.info("web.call.start type=%s model=%s details=%s", call_type, model, details)
    return started


def _log_web_success(call_type: str, model: str, started: float, **details: int) -> None:
    _LOGGER.info(
        "web.call.success type=%s model=%s duration_s=%.1f details=%s",
        call_type,
        model,
        time.monotonic() - started,
        details,
    )


def _log_web_failure(call_type: str, model: str, started: float, error: BaseException) -> None:
    _LOGGER.warning(
        "web.call.failure type=%s model=%s duration_s=%.1f error=%s",
        call_type,
        model,
        time.monotonic() - started,
        str(error)[:500],
    )
