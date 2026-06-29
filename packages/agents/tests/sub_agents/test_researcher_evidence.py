from __future__ import annotations

import pytest


class TestResearcherEvidence:
    @pytest.mark.asyncio
    async def test_build_research_evidence_compacts_raw_fetched_page(self) -> None:
        from packages.agents.sub_agents.researcher.evidence import build_research_evidence

        async def fetch_page(url: str) -> str:
            return f"important excerpt for {url} " + ("raw-page-noise " * 10_000)

        evidence = await build_research_evidence(
            [{"title": "Source", "url": "https://example.edu/source", "snippet": ""}],
            fetch_limit=1,
            web_fetcher=fetch_page,
        )

        fetched = evidence[0]
        assert fetched["fetch_status"] == "FETCHED"
        assert "excerpt" in fetched
        assert "content" not in fetched
        assert "important excerpt" in str(fetched["excerpt"])
        assert len(str(fetched["excerpt"])) < len("raw-page-noise " * 10_000)
