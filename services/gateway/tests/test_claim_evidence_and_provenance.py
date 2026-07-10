"""#432: claim-to-evidence persistence (fail-closed) and Decision Provenance assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.contracts.artifact_document import (
    ArtifactDocument,
    ArtifactPayload,
    DocumentBlock,
    DocumentSection,
)
from common.contracts.claim_evidence import ClaimEvidence
from services.gateway.artifact_document_store import ArtifactDocumentStore, ArtifactDocumentWrite
from services.gateway.claim_evidence_store import ClaimEvidenceStore, UngroundedHighRiskClaimError
from services.gateway.decision_provenance_service import assemble_decision_provenance
from services.gateway.models import Base
from services.gateway.teaching_pack_store import TeachingPackRunCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId, TeacherId

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession

DATABASE_URL = "postgresql+asyncpg://omc_dev:omc_dev@localhost:5432/oh_my_class"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()


async def _seed_document(session: AsyncSession, *, artifact_type: str = "recap") -> tuple[RunId, str]:
    run_id = RunId(f"test-{uuid4()}")
    await TeachingPackRunStore(session).create_run(TeachingPackRunCreate(
        run_id=run_id,
        teacher_id=TeacherId("teacher-provenance"),
        raw_request="Build a recap on boiling points",
        class_info={"grade": 5},
    ))
    document = ArtifactDocument(
        document_id=f"document-{uuid4()}",
        artifact_id="recap-1",
        artifact_type=artifact_type,  # type: ignore[arg-type]
        version=1,
        language="en",
        audience="student",
        authority="generated",
        payload=ArtifactPayload(
            payload_kind="block_document",
            sections=[DocumentSection(
                entity_id="section-1",
                title="Recap",
                blocks=[DocumentBlock(
                    entity_id="block-1", block_kind="paragraph", text="Water boils at 100C at sea level.",
                )],
            )],
        ),
    )
    await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(run_id=run_id, document=document))
    return run_id, document.document_id


async def test_ungrounded_high_risk_claim_is_rejected_before_writing_anything(session: AsyncSession) -> None:
    _, document_id = await _seed_document(session)
    claims = [
        ClaimEvidence(
            claim_id="claim-grounded",
            claim_text="Water boils at 100C at sea level.",
            risk_level="high",
            citation_ids=["src-1"],
            verification_status="VERIFIED",
        ),
        ClaimEvidence(
            claim_id="claim-ungrounded",
            claim_text="This fact is disputed.",
            risk_level="high",
            citation_ids=[],
            verification_status="UNCERTAIN",
        ),
    ]
    store = ClaimEvidenceStore(session)

    with pytest.raises(UngroundedHighRiskClaimError) as excinfo:
        await store.persist_for_document(document_id, claims)
    assert "claim-ungrounded" in excinfo.value.failures[0]

    persisted = await store.list_for_document(document_id)
    assert persisted == [], "the whole batch must be rejected, including the grounded claim"


async def test_grounded_claims_persist_and_assemble_into_decision_provenance(session: AsyncSession) -> None:
    _, document_id = await _seed_document(session)
    claim = ClaimEvidence(
        claim_id="claim-1",
        claim_text="Water boils at 100C at sea level.",
        risk_level="high",
        citation_ids=["src-1"],
        verification_status="VERIFIED",
    )
    await ClaimEvidenceStore(session).persist_for_document(document_id, [claim])

    provenance = await assemble_decision_provenance(session, document_id)

    assert provenance.document_id == document_id
    assert provenance.version == 1
    assert provenance.authority == "generated"
    assert provenance.claim_evidence == [claim]
    assert provenance.dependency_document_ids == []
    assert not hasattr(provenance, "raw_prompt")
