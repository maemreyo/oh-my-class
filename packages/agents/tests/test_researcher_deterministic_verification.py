"""researcher-001: deterministic verification replaces LLM-rated/fabricated credibility."""

from __future__ import annotations

from packages.agents.sub_agents.researcher.runtime_grounding import (
    _apply_deterministic_verification,
    target_terms,
)


def test_triangulation_overrides_llm_rated_status_and_credibility() -> None:
    bundle = {
        "sources": [
            {"title": "A", "url": "https://grammar.edu/x", "excerpt": "affect verb effect noun",
             "credibility_score": 0.99, "verification_status": "VERIFIED"},
            {"title": "B", "url": "https://writing.gov/y", "excerpt": "affect verb effect noun",
             "credibility_score": 0.99, "verification_status": "VERIFIED"},
            {"title": "C", "url": "https://blog.com/z", "excerpt": "",
             "credibility_score": 0.5, "verification_status": "VERIFIED"},
        ]
    }

    result = _apply_deterministic_verification(bundle, ["affect", "effect"])
    by_url = {s["url"]: s for s in result["sources"]}

    # Two independent domains corroborate -> VERIFIED; the LLM's 0.99 is replaced.
    assert by_url["https://grammar.edu/x"]["verification_status"] == "VERIFIED"
    assert by_url["https://writing.gov/y"]["verification_status"] == "VERIFIED"
    assert by_url["https://grammar.edu/x"]["credibility_score"] > 0.5

    # No fetched body -> cannot be verified; fabricated 0.5 replaced by a low computed value.
    assert by_url["https://blog.com/z"]["verification_status"] == "UNCERTAIN"
    assert by_url["https://blog.com/z"]["credibility_score"] <= 0.4


def test_single_domain_not_verified_even_if_llm_said_so() -> None:
    bundle = {
        "sources": [
            {"title": "A", "url": "https://grammar.edu/x", "excerpt": "affect effect",
             "credibility_score": 0.9, "verification_status": "VERIFIED"},
            {"title": "B", "url": "https://grammar.edu/y", "excerpt": "affect effect",
             "credibility_score": 0.9, "verification_status": "VERIFIED"},
        ]
    }
    result = _apply_deterministic_verification(bundle, ["affect", "effect"])
    assert {s["verification_status"] for s in result["sources"]} == {"UNCERTAIN"}


def test_target_terms_include_topic_and_objectives() -> None:
    terms = target_terms(
        {"learning_objectives": ["Explain photosynthesis", {"description": "compare cells"}]},
        "Biology",
    )
    assert "Biology" in terms
    assert "Explain photosynthesis" in terms
    assert "compare cells" in terms
