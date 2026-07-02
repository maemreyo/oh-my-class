from __future__ import annotations

from packages.agents.gates.fact_check.fact_checker import fact_check


def test_fact_check_uses_verified_grounding_corpus_without_llm() -> None:
    content = "Photosynthesis uses CO2 + H2O and the formula is x = a+b."
    corpus = [
        {
            "verification_status": "VERIFIED",
            "excerpt": "Photosynthesis uses CO2 + H2O and the formula is x = a+b.",
        },
        {
            "verification_status": "VERIFIED",
            "excerpt": "A second source also states photosynthesis uses CO2 + H2O and x = a+b.",
        },
    ]

    result = fact_check(content, grounding_corpus=corpus)

    assert result.passed is True
    assert result.llm_called is False
    assert result.grounded_claims
    assert result.uncertain_claims == []


def test_fact_check_marks_ungrounded_high_risk_claims_uncertain_when_llm_skipped() -> None:
    content = "The lesson says x = a+b."

    result = fact_check(content, grounding_corpus=[], skip_llm=True)

    assert result.passed is False
    assert result.llm_called is False
    assert result.grounded_claims == []
    assert result.uncertain_claims == ["x = a+b"]
