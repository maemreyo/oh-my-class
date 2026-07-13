"""Mandatory tenant guard around ArtifactContentStore (#472)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from common.contracts.content_factory.tenancy import TenantContext

if TYPE_CHECKING:
    from common.contracts.answer_set import AnswerSet
    from common.contracts.artifact import ArtifactContent
    from packages.agents.teaching_pack.content_orchestrator import (
        ArtifactContentStore,
        ArtifactDocumentReference,
        ArtifactDocumentReferenceState,
        ArtifactPersistenceResult,
    )


class TenantScopedArtifactContentStore:
    def __init__(self, delegate: ArtifactContentStore, tenant: TenantContext) -> None:
        self._delegate = delegate
        self._tenant = tenant

    async def persist(
        self,
        run_id: str,
        generation_id: str,
        artifact: ArtifactContent,
        artifact_id: str,
    ) -> ArtifactDocumentReference:
        from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult

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
        metadata = dict(result.artifact.metadata)
        existing_owner = metadata.get("organization_id")
        if isinstance(existing_owner, str):
            self._tenant.require_organization(existing_owner)
        metadata["organization_id"] = self._tenant.organization_id
        metadata["tenant_audit_fingerprint"] = self._tenant.audit_fingerprint
        artifact = result.artifact.model_copy(update={"metadata": metadata})
        from packages.agents.teaching_pack.content_orchestrator import ArtifactPersistenceResult as Result

        return await self._delegate.persist_result(
            run_id,
            generation_id,
            Result(
                artifact=artifact,
                answer_set=result.answer_set,
                dependency_document_ids=result.dependency_document_ids,
            ),
            artifact_id,
        )

    async def read_projection(self, document_id: str) -> ArtifactContent:
        projection = await self._delegate.read_projection(document_id)
        owner = projection.metadata.get("organization_id")
        if not isinstance(owner, str):
            raise PermissionError(f"artifact {document_id!r} has no organization ownership metadata")
        self._tenant.require_organization(owner)
        return projection

    async def read_projections(
        self,
        references: list[ArtifactDocumentReferenceState],
    ) -> list[ArtifactContent]:
        return [await self.read_projection(reference["document_id"]) for reference in references]

    async def read_answer_set(self, document_id: str) -> AnswerSet | None:
        await self.read_projection(document_id)
        return await self._delegate.read_answer_set(document_id)
