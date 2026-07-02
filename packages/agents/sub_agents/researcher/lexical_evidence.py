"""Per-cluster evidence gathering — the missing brick before lexical grounding.

Bridges a ``NormalizedVocabularyCluster`` to a ``LexicalGroundingRequest`` by reusing
the researcher's web search + fetch and the deterministic triangulation core. A source
is marked ``VERIFIED`` only when ≥2 independent domains corroborate the cluster terms —
the same mechanism the Layer-2 fact_check corpus uses. Search/fetch are injectable so
the composition is testable without network or LLM.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from common.contracts.vocabulary_batch import (
    LexicalGroundingRequest,
    LexicalGroundingSourceEvidence,
    NormalizedVocabularyCluster,
)
from packages.agents.sub_agents.researcher.evidence import WebFetcher, build_research_evidence
from packages.agents.sub_agents.researcher.triangulation import FetchedSource, triangulate

WebSearch = Callable[..., Awaitable[list[dict[str, Any]]]]

_EXCERPT_MAX = 2000  # LexicalGroundingSourceEvidence.excerpt max_length
_TITLE_MAX = 500


async def gather_cluster_evidence(
    cluster: NormalizedVocabularyCluster,
    cluster_snapshot_hash: str,
    run_id: str,
    *,
    web_search: WebSearch | None = None,
    web_fetcher: WebFetcher | None = None,
) -> LexicalGroundingRequest:
    """Search + fetch + triangulate evidence for a cluster's terms."""
    search = web_search or _default_web_search()
    fetcher = web_fetcher or _default_web_fetcher()
    from packages.agents.config.models import NINEROUTER

    query = " ".join(cluster.terms)
    candidates = await search(
        query, num_results=NINEROUTER.search_results, min_sources=NINEROUTER.min_sources
    )
    evidence = await build_research_evidence(
        candidates, fetch_limit=NINEROUTER.fetch_limit_standard, web_fetcher=fetcher
    )

    fetched = [
        FetchedSource(
            title=str(_source(entry).get("title", "")),
            url=_optional_str(_source(entry).get("url")),
            excerpt=str(entry.get("excerpt", "")),
        )
        for entry in evidence
        if entry.get("fetch_status") == "FETCHED" and entry.get("excerpt")
    ]
    triangulated = triangulate(fetched, cluster.terms)

    source_evidence = tuple(
        LexicalGroundingSourceEvidence(
            source_id=f"src-{cluster.cluster_id}-{index}"[:120],
            title=(result.source.title or "Untitled source")[:_TITLE_MAX],
            url=result.source.url,
            excerpt=result.source.excerpt[:_EXCERPT_MAX],
            verification_status=result.verification_status,  # type: ignore[arg-type]
        )
        for index, result in enumerate(triangulated)
        if result.source.excerpt.strip()
    )
    return LexicalGroundingRequest(
        cluster=cluster,
        source_evidence=source_evidence,
        cluster_snapshot_hash=cluster_snapshot_hash,
    )


def _source(entry: dict[str, Any]) -> dict[str, Any]:
    source = entry.get("source")
    return source if isinstance(source, dict) else {}


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _default_web_search() -> WebSearch:
    from packages.agents.tools.web_search import web_search

    return web_search


def _default_web_fetcher() -> WebFetcher:
    from packages.agents.sub_agents.researcher.tools import web_fetch

    return web_fetch
