"""Per-artifact-version approval, gated on blocking review notes (ADR-055)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

from services.gateway.artifact_document_store import ArtifactDocumentStore, ContentApprovalCreate
from services.gateway.review_note_store import ReviewNoteStore

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from services.gateway.teaching_pack_types import RunId


class ArtifactNotCurrentError(LookupError):
    """Raised when approving a version that is not the artifact's current head."""

    def __init__(self, artifact_id: str, requested_version: int, current_version: int) -> None:
        self.artifact_id = artifact_id
        self.requested_version = requested_version
        self.current_version = current_version
        super().__init__(
            f"{artifact_id} v{requested_version} is not current (current is v{current_version})",
        )


class BlockingReviewNotesOpenError(RuntimeError):
    """Raised when approving an artifact that still has an open blocking review note."""

    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id
        super().__init__(f"{artifact_id} has an open blocking review note")


@dataclass(frozen=True, slots=True)
class BulkApprovalResult:
    approved: list[str]
    blocked: list[dict[str, str]]


async def approve_artifact_version(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_id: str,
    version: int,
    approver_id: str,
) -> None:
    """Approve one artifact's current version. Raises if stale or blocked."""
    store = ArtifactDocumentStore(session)
    latest = await store.get_latest(run_id, artifact_id)
    if latest is None or latest.version != version:
        current = latest.version if latest is not None else 0
        raise ArtifactNotCurrentError(artifact_id, version, current)
    if await ReviewNoteStore(session).has_open_blocking(run_id, artifact_id):
        raise BlockingReviewNotesOpenError(artifact_id)
    await store.insert_approval(latest.document_id, _approval(approver_id))
    await session.flush()


async def approve_all_current(
    session: AsyncSession,
    *,
    run_id: RunId,
    artifact_ids: list[str],
    approver_id: str,
) -> BulkApprovalResult:
    """Approve every artifact in `artifact_ids` whose current version has no
    open blocking note. Never partially approves one artifact -- each either
    fully succeeds or is reported in `blocked` with why.
    """
    store = ArtifactDocumentStore(session)
    notes = ReviewNoteStore(session)
    approved: list[str] = []
    blocked: list[dict[str, str]] = []
    for artifact_id in artifact_ids:
        latest = await store.get_latest(run_id, artifact_id)
        if latest is None:
            blocked.append({"artifact_id": artifact_id, "reason": "no_version"})
            continue
        if await notes.has_open_blocking(run_id, artifact_id):
            blocked.append({"artifact_id": artifact_id, "reason": "blocking_review_note"})
            continue
        await store.insert_approval(latest.document_id, _approval(approver_id))
        approved.append(artifact_id)
    await session.flush()
    return BulkApprovalResult(approved=approved, blocked=blocked)


def _approval(approver_id: str) -> ContentApprovalCreate:
    return ContentApprovalCreate(
        approval_id=f"approval-{uuid4().hex[:16]}", status="approved", approved_by=approver_id,
    )
