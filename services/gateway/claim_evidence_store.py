"""Persistence for per-document claim-to-evidence mappings, fail-closed on save (ADR-054)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.claim_evidence import ClaimEvidence, assert_high_risk_claims_are_grounded
from services.gateway.source_collection_models import ClaimEvidenceRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class UngroundedHighRiskClaimError(ValueError):
    """Raised instead of persisting: a `high` risk_level claim lacks a citation or is unverified."""

    def __init__(self, failures: list[str]) -> None:
        self.failures = failures
        super().__init__(f"ungrounded high-risk claims: {', '.join(failures)}")


class ClaimEvidenceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_for_document(self, document_id: str, claims: list[ClaimEvidence]) -> None:
        """Persist `claims` for `document_id`, or raise before writing anything.

        Fail-closed per ADR-054: a document version with even one ungrounded
        high-risk claim is rejected outright, not saved-with-a-warning.
        """
        failures = assert_high_risk_claims_are_grounded(claims)
        if failures:
            raise UngroundedHighRiskClaimError([f"{f.claim_id} ({f.reason})" for f in failures])
        for index, claim in enumerate(claims):
            self._session.add(ClaimEvidenceRecord(
                claim_evidence_id=f"claimev-{document_id}-{index}",
                document_id=document_id,
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                risk_level=claim.risk_level,
                verification_status=claim.verification_status,
                citation_ids_json=claim.citation_ids,
            ))
        await self._session.flush()

    async def list_for_document(self, document_id: str) -> list[ClaimEvidence]:
        statement = select(ClaimEvidenceRecord).where(
            ClaimEvidenceRecord.document_id == document_id,
        )
        records = (await self._session.execute(statement)).scalars().all()
        return [
            ClaimEvidence(
                claim_id=r.claim_id,
                claim_text=r.claim_text,
                risk_level=r.risk_level,  # type: ignore[arg-type]
                citation_ids=r.citation_ids_json,
                verification_status=r.verification_status,  # type: ignore[arg-type]
            )
            for r in records
        ]
