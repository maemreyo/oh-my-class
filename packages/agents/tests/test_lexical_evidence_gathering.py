"""Deterministic test for per-cluster evidence gathering (no network/LLM).

Injects fake search + fetch and asserts triangulation marks ≥2-independent-domain
corroboration as VERIFIED in the resulting LexicalGroundingRequest.
"""

from __future__ import annotations

from typing import Any

import pytest

from common.contracts.vocabulary_batch import NormalizedVocabularyCluster
from packages.agents.sub_agents.researcher.lexical_evidence import gather_cluster_evidence

BODY = "Affect is a verb and effect is a noun in standard usage."


def _cluster() -> NormalizedVocabularyCluster:
    return NormalizedVocabularyCluster(
        cluster_id="affect-effect",
        terms=("affect", "effect"),
        raw_input_span="affect / effect",
        confidence=0.9,
    )


async def _fake_search(query: str, **_: Any) -> list[dict[str, Any]]:
    return [
        {"title": "Grammar EDU", "url": "https://grammar.edu/affect"},
        {"title": "Writing GOV", "url": "https://writing.gov/effect"},
        {"title": "No URL", "url": ""},
    ]


async def _fake_fetch(url: str) -> str:
    return BODY  # every fetched page corroborates the distinction


@pytest.mark.anyio
async def test_gather_marks_independent_corroboration_verified() -> None:
    request = await gather_cluster_evidence(
        _cluster(),
        cluster_snapshot_hash="hash-1",
        run_id="run-1",
        web_search=_fake_search,
        web_fetcher=_fake_fetch,
    )

    assert request.cluster_snapshot_hash == "hash-1"
    by_url = {e.url: e.verification_status for e in request.source_evidence}
    # Two independent domains (grammar.edu, writing.gov) corroborate -> VERIFIED.
    assert by_url["https://grammar.edu/affect"] == "VERIFIED"
    assert by_url["https://writing.gov/effect"] == "VERIFIED"
    # The candidate with no URL was skipped by fetch (url == "" -> SKIPPED).
    assert None not in by_url


@pytest.mark.anyio
async def test_gather_yields_uncertain_when_not_corroborated() -> None:
    async def _one_relevant(url: str) -> str:
        return BODY if "grammar" in url else "Unrelated text about the weather today."

    request = await gather_cluster_evidence(
        _cluster(),
        cluster_snapshot_hash="hash-2",
        run_id="run-1",
        web_search=_fake_search,
        web_fetcher=_one_relevant,
    )

    # Only one domain covers the terms -> nothing reaches VERIFIED.
    assert {e.verification_status for e in request.source_evidence} == {"UNCERTAIN"}
