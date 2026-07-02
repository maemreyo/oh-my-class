from __future__ import annotations

from datetime import UTC, datetime, timedelta

from packages.agents.sub_agents.researcher.grounding import (
    ClaimCriticality,
    GroundingCacheKey,
    ResearchMemoryCache,
    cache_key,
    policy_rigor,
    target_claims_from_lesson_plan,
    verified_sources_for_cache,
)


def test_target_claims_are_factual_and_criticality_tiered() -> None:
    claims = target_claims_from_lesson_plan({
        "topic": "Photosynthesis formula",
        "learning_objectives": [
            {"description": "Students will compare leaves in groups"},
            {"description": "Definition: photosynthesis converts CO2 + H2O into glucose"},
            "Plants release 6 molecules of oxygen",
        ],
    })

    by_text = {claim.text: claim.criticality for claim in claims}

    assert by_text["Photosynthesis formula"] is ClaimCriticality.CRITICAL
    assert by_text["Students will compare leaves in groups"] is ClaimCriticality.SKIP
    assert by_text["Definition: photosynthesis converts CO2 + H2O into glucose"] is ClaimCriticality.CRITICAL
    assert by_text["Plants release 6 molecules of oxygen"] is ClaimCriticality.MINOR


def test_policy_rigor_controls_thresholds_and_subject_recency() -> None:
    basic = policy_rigor("basic", "science")
    rigorous = policy_rigor("rigorous", "history")

    assert basic.min_independent_sources == 2
    assert basic.claim_coverage == 0.5
    assert basic.recency_days == 365
    assert rigorous.min_independent_sources == 3
    assert rigorous.claim_coverage == 0.9
    assert rigorous.sources_per_claim_cap == 10
    assert rigorous.recency_days == 1825


def test_research_memory_cache_reuses_fresh_entries_and_invalidates_stale_entries() -> None:
    cache = ResearchMemoryCache()
    key = GroundingCacheKey("Fractions", "5", "vi")
    now = datetime(2026, 7, 2, tzinfo=UTC)
    sources = ({"title": "A", "url": "https://a.edu", "excerpt": "fractions", "verification_status": "VERIFIED"},)

    cache.store(key, sources, now)

    assert cache.get(key, now=now + timedelta(days=30), recency_days=365) == sources
    assert cache.get(key, now=now + timedelta(days=366), recency_days=365) is None


def test_cache_key_and_verified_sources_use_topic_grade_locale() -> None:
    key = cache_key("Fractions", {"grade": 5, "language": "vi"})
    sources = verified_sources_for_cache([
        {"title": "A", "url": "https://a.edu", "excerpt": "fractions", "verification_status": "VERIFIED"},
        {"title": "B", "url": "https://b.edu", "excerpt": "", "verification_status": "UNCERTAIN"},
    ])

    assert key == GroundingCacheKey("Fractions", "5", "vi")
    assert sources == ({"title": "A", "url": "https://a.edu", "excerpt": "fractions", "verification_status": "VERIFIED"},)
