"""Registry-driven editing over the V2 ArtifactDocument lineage.

A "registry" here is the existing `ArtifactDocument._payload_matches_artifact_type`
validator: every artifact type already declares which payload shape it takes,
so one generic edit path works across all twelve surfaces without a
per-type branch. Callers only ever submit a full, typed `ArtifactPayload`
for the next version -- there is no separate merge/patch step to keep in
sync with the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select

from common.contracts.artifact_document import ArtifactDocument, ArtifactPayload
from services.gateway.artifact_document_models import (
    ArtifactDocumentRecord,
    ContentDependencyRecord,
)
from services.gateway.artifact_document_store import (
    ArtifactDocumentStore,
    ArtifactDocumentWrite,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


class ArtifactHasNoVersionsError(LookupError):
    """Raised when editing/restoring an artifact that has never been persisted as V2."""

    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(artifact_id)


class ArtifactVersionNotFoundError(LookupError):
    """Raised when restoring a version number that does not exist."""

    def __init__(self, artifact_id: str, version: int) -> None:
        self.artifact_id = artifact_id
        self.version = version
        super().__init__(f"{artifact_id} v{version}")


@dataclass(frozen=True, slots=True)
class EditOutcome:
    document: ArtifactDocument
    impacted_artifact_ids: list[str]


async def edit_artifact_document(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_id: str,
    base_version: int,
    payload: ArtifactPayload,
    authority: str,
) -> EditOutcome:
    """Create the next immutable version of `artifact_id`, iff `base_version` is current.

    Raises `StaleArtifactVersionError` (via the store) on an optimistic-lock
    conflict -- callers must reload the current version and retry.
    """
    store = ArtifactDocumentStore(session)
    latest = await store.get_latest(run_id, artifact_id)
    if latest is None:
        raise ArtifactHasNoVersionsError(artifact_id)
    next_document = ArtifactDocument(
        document_id=f"doc-{uuid4().hex[:16]}",
        artifact_id=artifact_id,
        artifact_type=latest.artifact_type,  # type: ignore[arg-type]
        version=latest.version + 1,
        language=latest.language,  # type: ignore[arg-type]
        audience=latest.audience,  # type: ignore[arg-type]
        authority=authority,  # type: ignore[arg-type]
        payload=payload,
        parent_document_id=latest.document_id,
        source_document_id=latest.source_document_id or latest.document_id,
    )
    persisted = await store.create_edit(
        run_id,
        base_version,
        ArtifactDocumentWrite(run_id=run_id, document=next_document),
    )
    impacted = await impacted_artifact_ids(session, latest.document_id)
    return EditOutcome(document=persisted.document, impacted_artifact_ids=impacted)


async def restore_artifact_document(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_id: str,
    target_version: int,
) -> EditOutcome:
    """Restore creates a *new* version carrying `target_version`'s payload.

    History is never mutated.
    """
    store = ArtifactDocumentStore(session)
    versions = await store.list_versions(run_id, artifact_id)
    if not versions:
        raise ArtifactHasNoVersionsError(artifact_id)
    target = next((record for record in versions if record.version == target_version), None)
    if target is None:
        raise ArtifactVersionNotFoundError(artifact_id, target_version)
    latest = versions[0]
    restored_payload = ArtifactPayload.model_validate(target.document_json["payload"])
    return await edit_artifact_document(
        session,
        run_id=run_id,
        artifact_id=artifact_id,
        base_version=latest.version,
        payload=restored_payload,
        authority="restored",
    )


async def impacted_artifact_ids(session: AsyncSession, edited_document_id: str) -> list[str]:
    """Dependency-impact hook: which other artifacts point at the version just superseded.

    Visible to the teacher as a heads-up, never auto-regenerated -- the
    workspace surfaces this list and the teacher chooses which scoped
    repairs to run (ADR-055). Public so other derivation services (e.g.
    `artifact_language_version_service`) can report staleness the same way
    edits and restores do, without duplicating the query.
    """
    statement = (
        select(ArtifactDocumentRecord.artifact_id)
        .join(
            ContentDependencyRecord,
            ContentDependencyRecord.document_id == ArtifactDocumentRecord.document_id,
        )
        .where(ContentDependencyRecord.source_document_id == edited_document_id)
        .distinct()
    )
    return [row[0] for row in (await session.execute(statement)).all()]
