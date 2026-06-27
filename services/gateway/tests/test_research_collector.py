from __future__ import annotations

from dataclasses import dataclass

import pytest

from common.contracts.run_contract import ContractRevisionMeta, RunContract
from services.gateway.research_collector import (
    CachedResearchProviders,
    FetchUnavailableError,
    ResearchCollectionRequest,
    ResearchProviders,
    collect_research_brief,
)
from services.gateway.research_engine import FetchResult, SearchCandidate, plan_search


class TestResearchCollector:
    @pytest.mark.anyio
    async def test_collects_compact_brief_from_deduped_ranked_sources(self) -> None:
        providers = FakeProviders(
            search_results=(
                SearchCandidate("A", "https://edu.test/fractions?utm=x", "curriculum"),
                SearchCandidate("A duplicate", "http://edu.test/fractions#top", "duplicate"),
                SearchCandidate("Blocked", "https://blocked.test/a", "blocked"),
                SearchCandidate("Teacher", "https://teacher.test/fractions", "teacher"),
            ),
            fetch_results={
                "https://teacher.test/fractions": (
                    "Teacher source confirms fraction misconception guidance."
                ),
                "https://edu.test/fractions": "Curriculum source explains equivalent fractions.",
            },
        )

        brief = await collect_research_brief(
            ResearchCollectionRequest(
                contract=_contract(),
                plan=plan_search(_contract()),
                blocked_domains=frozenset({"blocked.test"}),
                preferred_domains=frozenset({"edu.test"}),
                teacher_sources=frozenset({"https://teacher.test/fractions"}),
                max_per_domain=2,
            ),
            providers,
        )

        assert [citation.source_id for citation in brief.citations] == ["source-1", "source-2"]
        assert brief.citations[0].url == "https://teacher.test/fractions"
        assert all("duplicate" not in finding for finding in brief.key_findings)
        assert all("blocked" not in finding for finding in brief.key_findings)

    @pytest.mark.anyio
    async def test_fetch_failure_does_not_fail_whole_research_run(self) -> None:
        providers = FakeProviders(
            search_results=(
                SearchCandidate("A", "https://edu.test/a", "good"),
                SearchCandidate("B", "https://other.test/b", "fails"),
            ),
            fetch_results={"https://edu.test/a": "Useful evidence survives."},
            failing_urls=frozenset({"https://other.test/b"}),
        )

        brief = await collect_research_brief(
            ResearchCollectionRequest(
                contract=_contract(topic="Photosynthesis", subject="science"),
                plan=plan_search(_contract(topic="Photosynthesis", subject="science")),
                blocked_domains=frozenset(),
                preferred_domains=frozenset(),
                teacher_sources=frozenset(),
                max_per_domain=2,
            ),
            providers,
        )

        assert [citation.url for citation in brief.citations] == ["https://edu.test/a"]
        assert brief.key_findings == ["Useful evidence survives."]

    @pytest.mark.anyio
    async def test_cached_provider_reuses_search_and_fetch_within_ttl(self) -> None:
        providers = CountingProviders(
            search_results=(SearchCandidate("A", "https://edu.test/a", "good"),),
            fetch_results={"https://edu.test/a": "Useful evidence."},
        )
        cached = CachedResearchProviders(providers, ttl_seconds=60)

        first_search = await cached.search("fractions")
        second_search = await cached.search("fractions")
        first_fetch = await cached.fetch("source-1", "https://edu.test/a")
        second_fetch = await cached.fetch("source-1", "https://edu.test/a")

        assert first_search == second_search
        assert first_fetch == second_fetch
        assert providers.search_count == 1
        assert providers.fetch_count == 1


@dataclass(frozen=True, slots=True)
class FakeProviders(ResearchProviders):
    search_results: tuple[SearchCandidate, ...]
    fetch_results: dict[str, str]
    failing_urls: frozenset[str] = frozenset()

    async def search(self, query: str) -> tuple[SearchCandidate, ...]:
        return self.search_results

    async def fetch(self, source_id: str, url: str) -> FetchResult:
        if url in self.failing_urls:
            raise FetchUnavailableError(url)
        return FetchResult(source_id=source_id, content=self.fetch_results[url])


@dataclass(slots=True)
class CountingProviders(ResearchProviders):
    search_results: tuple[SearchCandidate, ...]
    fetch_results: dict[str, str]
    search_count: int = 0
    fetch_count: int = 0

    async def search(self, query: str) -> tuple[SearchCandidate, ...]:
        self.search_count += 1
        return self.search_results

    async def fetch(self, source_id: str, url: str) -> FetchResult:
        self.fetch_count += 1
        return FetchResult(source_id=source_id, content=self.fetch_results[url])


def _contract(
    *,
    topic: str = "Fractions",
    subject: str = "math",
) -> RunContract:
    return RunContract(
        contract_id="contract-test",
        run_id="run-test",
        teacher_id="teacher-test",
        topic=topic,
        grade_band="Grade 5",
        subject=subject,
        locale="en-US",
        instruction_language="en",
        curriculum="Common Core",
        citation_locale="en-US",
        artifact_types=["lesson"],
        export_formats=["html"],
        research_policy="standard",
        config_version="test",
        config_hash="0" * 64,
        revision_meta=ContractRevisionMeta(
            revision=1,
            actor="system",
            source="request",
            reason="test",
            effective_stage="setup_contract",
        ),
    )
