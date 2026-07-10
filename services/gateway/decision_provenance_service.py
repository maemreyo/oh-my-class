"""Assembles Decision Provenance from persisted domain records, never from raw traces (ADR-057)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from common.contracts.decision_provenance import DecisionProvenance
from services.gateway.artifact_document_models import (
    ArtifactDocumentRecord,
    ContentDependencyRecord,
)
from services.gateway.claim_evidence_store import ClaimEvidenceStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class DecisionProvenanceDocumentNotFoundError(LookupError):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(document_id)


async def assemble_decision_provenance(
    session: AsyncSession, document_id: str,
) -> DecisionProvenance:
    """Build the teacher-facing provenance record for one document version.

    Reads only durable domain rows (`artifact_documents`, `content_dependencies`,
    `claim_evidence`) -- there is no raw prompt, chain-of-thought, or provider
    trace anywhere in this path for `DecisionProvenance`'s closed schema to
    accidentally carry.
    """
    document = await session.get(ArtifactDocumentRecord, document_id)
    if document is None:
        raise DecisionProvenanceDocumentNotFoundError(document_id)
    claims = await ClaimEvidenceStore(session).list_for_document(document_id)
    dependency_statement = select(ContentDependencyRecord.source_document_id).where(
        ContentDependencyRecord.document_id == document_id,
    )
    dependency_ids = [row[0] for row in (await session.execute(dependency_statement)).all()]
    return DecisionProvenance(
        document_id=document.document_id,
        version=document.version,
        authority=document.authority,  # type: ignore[arg-type]
        claim_evidence=claims,
        dependency_document_ids=dependency_ids,
    )
