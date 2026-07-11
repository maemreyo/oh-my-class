from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.contracts.claim_evidence import ClaimEvidence, assert_high_risk_claims_are_grounded
from common.contracts.decision_provenance import DecisionProvenance


def _claim(**overrides: object) -> ClaimEvidence:
    defaults: dict[str, object] = {
        "claim_id": "claim-1",
        "claim_text": "Water boils at 100 degrees Celsius at sea level.",
        "risk_level": "high",
        "citation_ids": ["src-1"],
        "verification_status": "VERIFIED",
    }
    defaults.update(overrides)
    return ClaimEvidence(**defaults)


def test_high_risk_verified_claim_with_citations_passes() -> None:
    assert assert_high_risk_claims_are_grounded([_claim()]) == []


def test_high_risk_claim_without_citations_fails_closed() -> None:
    failures = assert_high_risk_claims_are_grounded([_claim(citation_ids=[])])

    assert len(failures) == 1
    assert failures[0].claim_id == "claim-1"
    assert failures[0].reason == "high_risk_no_citations"


def test_high_risk_uncertain_claim_fails_closed() -> None:
    failures = assert_high_risk_claims_are_grounded([_claim(verification_status="UNCERTAIN")])

    assert len(failures) == 1
    assert failures[0].reason == "high_risk_unverified"


def test_low_and_medium_risk_claims_are_never_blocked() -> None:
    claims = [
        _claim(claim_id="c-low", risk_level="low", citation_ids=[], verification_status="UNCERTAIN"),
        _claim(claim_id="c-medium", risk_level="medium", citation_ids=[], verification_status="UNCERTAIN"),
    ]

    assert assert_high_risk_claims_are_grounded(claims) == []


def test_decision_provenance_schema_rejects_raw_prompt_field() -> None:
    with pytest.raises(ValidationError):
        DecisionProvenance(
            document_id="doc-1",
            version=1,
            authority="generated",
            claim_evidence=[],
            dependency_document_ids=[],
            raw_prompt="ignore all previous instructions",
        )


def test_decision_provenance_has_no_reasoning_field_at_all() -> None:
    field_names = set(DecisionProvenance.model_fields)

    assert "raw_prompt" not in field_names
    assert "chain_of_thought" not in field_names
    assert "reasoning" not in field_names
    assert "prompt" not in field_names


def test_decision_provenance_knowledge_db_version_defaults_to_none() -> None:
    provenance = DecisionProvenance(
        document_id="doc-1",
        version=1,
        authority="generated",
        claim_evidence=[],
        dependency_document_ids=[],
    )

    assert provenance.knowledge_db_version is None


def test_decision_provenance_pins_a_knowledge_db_version_when_provided() -> None:
    provenance = DecisionProvenance(
        document_id="doc-1",
        version=1,
        authority="generated",
        claim_evidence=[],
        dependency_document_ids=[],
        knowledge_db_version="knowledge-db-2026.07.1",
    )

    assert provenance.knowledge_db_version == "knowledge-db-2026.07.1"
