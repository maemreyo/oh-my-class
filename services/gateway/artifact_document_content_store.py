from __future__ import annotations

from typing import TYPE_CHECKING

from common.contracts.artifact_projection_mapper import (
    artifact_content_from_document,
    artifact_document_from_content,
)
from packages.agents.teaching_pack.content_orchestrator import (
    ArtifactDocumentReference,
    ArtifactDocumentReferenceState,
    ArtifactPersistenceResult,
)
from services.gateway.artifact_document_store import (
    ArtifactDocumentStore,
    ArtifactDocumentWrite,
    ContentDependencyCreate,
)
from services.gateway.teaching_pack_types import RunId

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class GatewayArtifactDocumentContentStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def persist(self, run_id: str, generation_id: str, artifact, artifact_id: str) -> ArtifactDocumentReference:
        return await self.persist_result(
            run_id,
            generation_id,
            ArtifactPersistenceResult(artifact=artifact),
            artifact_id,
        )

    async def persist_result(
        self,
        run_id: str,
        generation_id: str,
        result: ArtifactPersistenceResult,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        document_id = f"{generation_id}:{artifact_id}"
        document = artifact_document_from_content(
            result.artifact,
            document_id=document_id,
            artifact_id=artifact_id,
        )
        answer_set = result.answer_set
        if answer_set is not None:
            answer_set = answer_set.model_copy(update={
                "source_document_id": document_id,
                "source_version": document.version,
                "answer_set_id": f"answers-{document_id}-v{document.version}",
            })
        async with self._session_factory() as session:
            async with session.begin():
                await ArtifactDocumentStore(session).persist(ArtifactDocumentWrite(
                    run_id=RunId(run_id),
                    document=document,
                    answer_set=answer_set,
                    dependencies=tuple(
                        ContentDependencyCreate(
                            source_document_id=document_id,
                            dependency_kind="answer_projection",
                        )
                        for document_id in result.dependency_document_ids
                    ),
                ))
        return ArtifactDocumentReference(
            document_id=document.document_id,
            artifact_id=document.artifact_id,
            artifact_type=document.artifact_type,
            generation_id=generation_id,
            version=document.version,
            title=document.title,
        )

    async def read_projection(self, document_id: str):
        async with self._session_factory() as session:
            persisted = await ArtifactDocumentStore(session).get_persisted(document_id)
        return artifact_content_from_document(persisted.document)

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ):
        return [await self.read_projection(reference["document_id"]) for reference in references]

    async def read_answer_set(self, document_id: str):
        async with self._session_factory() as session:
            persisted = await ArtifactDocumentStore(session).get_persisted(document_id)
        return persisted.answer_set
