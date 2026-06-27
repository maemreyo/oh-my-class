from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol

import anyio

from services.gateway.research_engine import (
    build_research_brief,
    extract_evidence,
    normalize_search_candidates,
    rank_search_candidates,
)

if TYPE_CHECKING:
    from common.contracts.research_brief import ResearchBrief
    from common.contracts.run_contract import RunContract
    from services.gateway.research_engine import FetchResult, SearchCandidate, SearchPlan


class ResearchProviders(Protocol):
    async def search(self, query: str) -> tuple[SearchCandidate, ...]: ...

    async def fetch(self, source_id: str, url: str) -> FetchResult: ...


@dataclass(frozen=True, slots=True)
class ResearchCollectionRequest:
    contract: RunContract
    plan: SearchPlan
    blocked_domains: frozenset[str]
    preferred_domains: frozenset[str]
    teacher_sources: frozenset[str]
    max_per_domain: int


class FetchUnavailableError(RuntimeError):
    def __init__(self, url: str) -> None:
        super().__init__(url)
        self.url = url


@dataclass(frozen=True, slots=True)
class CachedResearchProviders:
    providers: ResearchProviders
    ttl_seconds: int = 900
    _search_cache: dict[str, _CacheEntry[tuple[SearchCandidate, ...]]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )
    _fetch_cache: dict[str, _CacheEntry[FetchResult]] = field(
        default_factory=dict,
        init=False,
        repr=False,
    )

    async def search(self, query: str) -> tuple[SearchCandidate, ...]:
        cache = self._search_cache
        cached = cache.get(query)
        if cached is not None and cached.expires_at > datetime.now(UTC):
            return cached.value
        value = await self.providers.search(query)
        cache[query] = _CacheEntry(value=value, expires_at=_expires_at(self.ttl_seconds))
        return value

    async def fetch(self, source_id: str, url: str) -> FetchResult:
        cache = self._fetch_cache
        key = f"{source_id}:{url}"
        cached = cache.get(key)
        if cached is not None and cached.expires_at > datetime.now(UTC):
            return cached.value
        value = await self.providers.fetch(source_id, url)
        cache[key] = _CacheEntry(value=value, expires_at=_expires_at(self.ttl_seconds))
        return value


@dataclass(frozen=True, slots=True)
class _CacheEntry[T]:
    value: T
    expires_at: datetime


async def collect_research_brief(
    request: ResearchCollectionRequest,
    providers: ResearchProviders,
) -> ResearchBrief:
    candidates = await _collect_candidates(request.plan, providers)
    normalized = normalize_search_candidates(candidates, blocked_domains=request.blocked_domains)
    ranked = rank_search_candidates(
        normalized,
        teacher_sources=request.teacher_sources,
        preferred_domains=request.preferred_domains,
        max_per_domain=request.max_per_domain,
    )
    fetches = await _fetch_ranked_sources(ranked, providers)
    evidence = extract_evidence(fetches, ranked)
    return build_research_brief(
        topic=request.contract.topic,
        subject=request.contract.subject,
        evidence=evidence,
        ranked_candidates=ranked,
    )


async def _collect_candidates(
    plan: SearchPlan,
    providers: ResearchProviders,
) -> tuple[SearchCandidate, ...]:
    collected: list[SearchCandidate] = []

    async def collect_one(query: str) -> None:
        collected.extend(await providers.search(query))

    async with anyio.create_task_group() as task_group:
        for query in plan.queries:
            task_group.start_soon(collect_one, query.query)
    return tuple(collected)


async def _fetch_ranked_sources(
    ranked,
    providers: ResearchProviders,
) -> tuple[FetchResult, ...]:
    fetches: list[FetchResult] = []

    async def fetch_one(source_id: str, url: str) -> None:
        try:
            fetches.append(await providers.fetch(source_id, url))
        except FetchUnavailableError:
            return

    async with anyio.create_task_group() as task_group:
        for candidate in ranked:
            task_group.start_soon(fetch_one, candidate.source_id, candidate.url)
    return tuple(fetches)


def _expires_at(ttl_seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=ttl_seconds)
