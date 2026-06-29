from __future__ import annotations

from typing import Protocol

import httpx

from packages.agents.config.models import NINEROUTER


class WebFetcher(Protocol):
    async def __call__(self, url: str) -> str: ...


async def build_research_evidence(
    source_candidates: list[dict[str, str]],
    *,
    fetch_limit: int,
    web_fetcher: WebFetcher,
) -> list[dict[str, dict[str, str] | str]]:
    evidence: list[dict[str, dict[str, str] | str]] = []
    for source in source_candidates[:fetch_limit]:
        url = source.get("url", "")
        if url == "":
            evidence.append({"source": source, "fetch_status": "SKIPPED", "excerpt": ""})
            continue
        try:
            content = await web_fetcher(url)
        except (httpx.HTTPError, ValueError) as error:
            evidence.append({
                "source": source,
                "fetch_status": "FAILED",
                "error": str(error)[:200],
                "excerpt": "",
            })
            continue
        evidence.append({
            "source": source,
            "fetch_status": "FETCHED",
            "excerpt": _compact_excerpt(content),
        })
    return evidence


def _compact_excerpt(content: str) -> str:
    normalized = " ".join(content.split())
    return normalized[: NINEROUTER.content_truncate]
