from __future__ import annotations

import pytest

from packages.quality.layer2_content.fact_check import FACTChecker, VerificationTag


@pytest.mark.anyio
async def test_fact_check_verifies_claim_against_two_research_sources() -> None:
    checker = FACTChecker(min_sources=2)

    claims = await checker.check_claims(
        "The French Revolution began in 1789.",
        [
            {"title": "History A", "content": "The French Revolution began in 1789."},
            {"title": "History B", "content": "In 1789, the French Revolution began."},
        ],
    )

    assert claims[0].tag is VerificationTag.VERIFIED
    assert claims[0].confidence == 1.0
    assert len(claims[0].sources) == 2


@pytest.mark.anyio
async def test_fact_check_flags_unsupported_claim_when_sources_disagree() -> None:
    checker = FACTChecker(min_sources=2)

    claims = await checker.check_claims(
        "The French Revolution began in 1789.",
        [{"title": "History", "content": "The French Revolution began in 1787."}],
    )

    assert claims[0].tag is VerificationTag.UNCERTAIN
    assert claims[0].confidence == 0.0


@pytest.mark.anyio
async def test_fact_check_reports_claims_unmeasured_without_sources() -> None:
    checker = FACTChecker(min_sources=2)

    claims = await checker.check_claims("Water is H2O.", [])

    assert claims[0].tag is VerificationTag.UNCERTAIN
    assert claims[0].sources == []
