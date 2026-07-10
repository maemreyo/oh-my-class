"""Append-only V2 artifact-document persistence with bounded V1 preview reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from common.contracts.answer_set import AnswerSet
from common.contracts.artifact_document import ArtifactDocument
from services.gateway.artifact_document_models import (
    AnswerSetRecord,
    ArtifactDocumentRecord,
    ArtifactDocumentSnapshotRecord,
    ContentApprovalRecord,
    ContentDependencyRecord,
    ContentVariantRecord,
)
from services.gateway.teaching_pack_snapshot_models import ArtifactSnapshot

if TYPE_CHECKING:
    from services.gateway.teaching_pack_types import JsonObject, RunId
    from sqlalchemy.ext.asyncio import AsyncSession


type ApprovalStatus = Literal["approved", "rejected", "pending"]
type VariantKind = Literal["semantic_support", "challenge", "language_scaffold", "accessibility"]
type DependencyKind = Literal["answer_projection", "variant", "snapshot", "export"]
type PreviewSchemaVersion = Literal["v1", "v2"]


@dataclass(frozen=True, slots=True)
class ContentApprovalCreate:
    approval_id: str
    status: ApprovalStatus
    approved_by: str


@dataclass(frozen=True, slots=True)
class ContentVariantCreate:
    variant_id: str
    variant_kind: VariantKind
    source_document_id: str


@dataclass(frozen=True, slots=True)
class ContentDependencyCreate:
    source_document_id: str
    dependency_kind: DependencyKind


@dataclass(frozen=True, slots=True)
class ArtifactDocumentWrite:
    run_id: RunId
    document: ArtifactDocument
    answer_set: AnswerSet | None = None
    variant: ContentVariantCreate | None = None
    dependencies: tuple[ContentDependencyCreate, ...] = ()
    approval: ContentApprovalCreate | None = None
    snapshot_id: str | None = None


@dataclass(frozen=True, slots=True)
class PersistedArtifactDocument:
    document: ArtifactDocument
    answer_set: AnswerSet | None
    approval_status: ApprovalStatus | None


@dataclass(frozen=True, slots=True)
class ArtifactPreviewSource:
    schema_version: PreviewSchemaVersion
    snapshot_id: str
    content_json: JsonObject


class ArtifactDocumentNotFoundError(LookupError):
    """Raised when a requested V2 document record is absent."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(document_id)


class ArtifactPreviewSourceNotFoundError(LookupError):
    """Raised when neither the V2 link nor legacy snapshot exists."""

    def __init__(self, snapshot_id: str) -> None:
        self.snapshot_id = snapshot_id
        super().__init__(snapshot_id)


class ArtifactDocumentStore:
    """Stores V2 records once and reads V1 snapshots only when V2 is absent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist(self, write: ArtifactDocumentWrite) -> PersistedArtifactDocument:
        """Insert immutable V2 lineage rows; repeated writes are idempotent."""
        document = write.document
        await self._session.execute(
            pg_insert(ArtifactDocumentRecord)
            .values(
                document_id=document.document_id,
                run_id=write.run_id,
                artifact_id=document.artifact_id,
                artifact_type=document.artifact_type,
                version=document.version,
                language=document.language,
                audience=document.audience,
                authority=document.authority,
                parent_document_id=document.parent_document_id,
                source_document_id=document.source_document_id,
                document_json=document.model_dump(mode="json"),
            )
            .on_conflict_do_nothing(index_elements=["document_id"]),
        )
        if write.answer_set is not None:
            await self._insert_answer_set(write.answer_set)
        if write.variant is not None:
            await self._insert_variant(document.document_id, write.variant)
        for dependency in write.dependencies:
            await self._insert_dependency(document.document_id, dependency)
        if write.approval is not None:
            await self._insert_approval(document.document_id, write.approval)
        if write.snapshot_id is not None:
            await self._insert_snapshot_link(document.document_id, write.snapshot_id)
        await self._session.flush()
        return await self._read_persisted(document.document_id)

    async def get_preview_source(
        self,
        run_id: RunId,
        document_id: str,
        snapshot_id: str,
    ) -> ArtifactPreviewSource:
        """Return V2 content when linked; otherwise expose the legacy V1 snapshot."""
        v2_statement = (
            select(ArtifactDocumentRecord.document_json, ArtifactDocumentSnapshotRecord.snapshot_id)
            .join(
                ArtifactDocumentSnapshotRecord,
                ArtifactDocumentSnapshotRecord.document_id == ArtifactDocumentRecord.document_id,
            )
            .where(
                ArtifactDocumentRecord.run_id == run_id,
                ArtifactDocumentRecord.document_id == document_id,
                ArtifactDocumentSnapshotRecord.snapshot_id == snapshot_id,
            )
        )
        v2 = (await self._session.execute(v2_statement)).one_or_none()
        if v2 is not None:
            return ArtifactPreviewSource(schema_version="v2", snapshot_id=v2.snapshot_id, content_json=v2.document_json)
        v1_statement = select(ArtifactSnapshot.content_json).where(
            ArtifactSnapshot.run_id == run_id,
            ArtifactSnapshot.snapshot_id == snapshot_id,
        )
        v1 = (await self._session.execute(v1_statement)).scalar_one_or_none()
        if v1 is None:
            raise ArtifactPreviewSourceNotFoundError(snapshot_id)
        return ArtifactPreviewSource(schema_version="v1", snapshot_id=snapshot_id, content_json=v1)

    async def _insert_answer_set(self, answer_set: AnswerSet) -> None:
        await self._session.execute(
            pg_insert(AnswerSetRecord)
            .values(
                answer_set_id=answer_set.answer_set_id,
                source_document_id=answer_set.source_document_id,
                source_version=answer_set.source_version,
                authority=answer_set.authority,
                answer_set_json=answer_set.model_dump(mode="json"),
            )
            .on_conflict_do_nothing(constraint="uq_answer_sets_document_version"),
        )

    async def _insert_variant(self, document_id: str, variant: ContentVariantCreate) -> None:
        await self._session.execute(
            pg_insert(ContentVariantRecord)
            .values(
                variant_id=variant.variant_id,
                document_id=document_id,
                source_document_id=variant.source_document_id,
                variant_kind=variant.variant_kind,
            )
            .on_conflict_do_nothing(constraint="uq_content_variants_document_kind"),
        )

    async def _insert_dependency(self, document_id: str, dependency: ContentDependencyCreate) -> None:
        await self._session.execute(
            pg_insert(ContentDependencyRecord)
            .values(
                document_id=document_id,
                source_document_id=dependency.source_document_id,
                dependency_kind=dependency.dependency_kind,
            )
            .on_conflict_do_nothing(constraint="uq_content_dependencies_edge"),
        )

    async def _insert_approval(self, document_id: str, approval: ContentApprovalCreate) -> None:
        await self._session.execute(
            pg_insert(ContentApprovalRecord)
            .values(
                approval_id=approval.approval_id,
                document_id=document_id,
                status=approval.status,
                approved_by=approval.approved_by,
            )
            .on_conflict_do_nothing(index_elements=["approval_id"]),
        )

    async def _insert_snapshot_link(self, document_id: str, snapshot_id: str) -> None:
        await self._session.execute(
            pg_insert(ArtifactDocumentSnapshotRecord)
            .values(document_id=document_id, snapshot_id=snapshot_id)
            .on_conflict_do_nothing(index_elements=["document_id", "snapshot_id"]),
        )

    async def _read_persisted(self, document_id: str) -> PersistedArtifactDocument:
        document_record = await self._session.get(ArtifactDocumentRecord, document_id)
        if document_record is None:
            raise ArtifactDocumentNotFoundError(document_id)
        answer_statement = select(AnswerSetRecord.answer_set_json).where(
            AnswerSetRecord.source_document_id == document_id,
            AnswerSetRecord.source_version == document_record.version,
        )
        answer_json = (await self._session.execute(answer_statement)).scalar_one_or_none()
        approval_statement = (
            select(ContentApprovalRecord.status)
            .where(ContentApprovalRecord.document_id == document_id)
            .order_by(ContentApprovalRecord.created_at.desc())
            .limit(1)
        )
        approval_status = (await self._session.execute(approval_statement)).scalar_one_or_none()
        return PersistedArtifactDocument(
            document=ArtifactDocument.model_validate(document_record.document_json),
            answer_set=AnswerSet.model_validate(answer_json) if answer_json is not None else None,
            approval_status=approval_status,
        )
