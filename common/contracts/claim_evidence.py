"""Claim-to-evidence mappings and the high-risk fail-closed grounding rule (ADR-054)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from common.contracts.research_brief import ResearchRiskLevel  # noqa: TC001


class ClaimEvidence(BaseModel):
    """One claim in an artifact, mapped to the citations that support it.

    Persisted per document version so Decision Provenance can show teachers
    exactly which source backs which claim (ADR-055) without exposing how
    the claim was produced.
    """

    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(min_length=1, max_length=80)
    claim_text: str = Field(min_length=1, max_length=2_000)
    risk_level: ResearchRiskLevel
    citation_ids: list[str] = Field(default_factory=list)
    verification_status: Literal["VERIFIED", "MODIFIED", "REMOVED", "UNCERTAIN"]


ClaimGroundingFailureReason = Literal["high_risk_no_citations", "high_risk_unverified"]


class ClaimGroundingFailure(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    reason: ClaimGroundingFailureReason


def assert_high_risk_claims_are_grounded(
    claims: list[ClaimEvidence],
) -> list[ClaimGroundingFailure]:
    """Fail-closed check (ADR-054): a `high` risk_level claim must carry at least one
    citation and be `VERIFIED` -- `UNCERTAIN`/`MODIFIED`/`REMOVED` claims must never
    silently reach a student. Returns the failures; callers must block persistence
    of any document that still has one, not persist-then-warn.
    """
    failures: list[ClaimGroundingFailure] = []
    for claim in claims:
        if claim.risk_level != "high":
            continue
        if not claim.citation_ids:
            failures.append(
                ClaimGroundingFailure(claim_id=claim.claim_id, reason="high_risk_no_citations"),
            )
        elif claim.verification_status != "VERIFIED":
            failures.append(
                ClaimGroundingFailure(claim_id=claim.claim_id, reason="high_risk_unverified"),
            )
    return failures
