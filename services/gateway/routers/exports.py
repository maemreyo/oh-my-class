"""Export listing, staleness, and regeneration endpoints (SDE-06).

Mostly read-only: per-artifact exports are produced by the teaching-pack
export pipeline (services/gateway/teaching_pack_completion.py) or the
explicit `/exports/regenerate` trigger below, a teacher action, never
something automatic. `/exports/teaching-pack` is the one other explicit
trigger here: it bundles every approved artifact in a run into a single
standalone HTML document via the renderer's `teaching_pack` plugin (#453),
distinct from -- and not gated by the same capability matrix as -- the
per-artifact export path.

Mounted the same way as SDE-05's version-history routes
(teaching_pack_previews.py): prefix `/teaching-packs`, dual `/run/` and
`/runs/` path aliases, DB-backed ownership check via `get_run_with_ownership`
-- these are the real (snapshot-store-backed) artifacts the deck editor
works against, not the legacy in-memory `/run/{run_id}/artifacts` dict.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING, Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.export_manifest_service import (
    ExportFormatNotImplementedError,
    UnsupportedExportPairError,
    regenerate_stale_exports,
)
from services.gateway.routers.teaching_pack_deps import (
    TEACHING_PACK_SESSION,
    get_run_with_ownership,
)
from services.gateway.teaching_pack_export_store import (
    ExportRecordCreate,
    ExportRecordRead,
    TeachingPackExportStore,
)
from services.gateway.teaching_pack_export_writer import TeachingPackBundleWriter

if TYPE_CHECKING:
    from services.gateway.teaching_pack_snapshot_schemas import ArtifactSnapshotRead
from services.gateway.teaching_pack_snapshot_store import TeachingPackSnapshotStore
from services.gateway.teaching_pack_types import RunId

router = APIRouter()


class ExportRecordResponse(BaseModel):
    export_id: str
    artifact_id: str
    snapshot_id: str
    format: str
    storage_path: str
    capability_version: str | None
    created_at: datetime


class FormatStalenessEntry(BaseModel):
    format: str
    latest_export: ExportRecordResponse | None
    stale: bool


class ExportStatusByFormatResponse(BaseModel):
    artifact_id: str
    current_snapshot_id: str | None
    formats: list[FormatStalenessEntry]


class RegenerateExportsRequest(BaseModel):
    formats: list[str] | None = Field(
        default=None, description="Defaults to every already-exported format.",
    )


class RegenerateExportsResponse(BaseModel):
    regenerated: list[str]
    reused: list[str]


class ExportStatusResponse(BaseModel):
    artifact_id: str
    current_snapshot_id: str | None
    latest_export: ExportRecordResponse | None
    stale: bool


def _to_response(record: ExportRecordRead) -> ExportRecordResponse:
    return ExportRecordResponse(
        export_id=record.export_id,
        artifact_id=record.artifact_id,
        snapshot_id=record.snapshot_id,
        format=record.format,
        storage_path=record.storage_path,
        capability_version=record.capability_version,
        created_at=record.created_at,
    )


@router.get("/run/{run_id}/exports", response_model=list[ExportRecordResponse])  # pyright: ignore[reportUntypedFunctionDecorator]
@router.get("/runs/{run_id}/exports", response_model=list[ExportRecordResponse])  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_exports(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    artifact_id: str | None = None,
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> list[ExportRecordResponse]:
    """List export records for a run, newest first.

    Older exports are never deleted or overwritten by later edits (SDE-06
    AC1/AC4), so this always includes every export still on disk/storage,
    not just the latest.
    """
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)
    store = TeachingPackExportStore(session)
    records = await store.list_exports(typed_run_id, artifact_id)
    return [_to_response(record) for record in records]


@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/artifacts/{artifact_id}/export-status",
    response_model=ExportStatusResponse,
)
@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/artifacts/{artifact_id}/export-status",
    response_model=ExportStatusResponse,
)
async def get_export_status(
    run_id: str,
    artifact_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ExportStatusResponse:
    """Staleness check: does the latest export lag the artifact's current head?"""
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)

    export_store = TeachingPackExportStore(session)
    snapshot_store = TeachingPackSnapshotStore(session)
    latest_export = await export_store.get_latest_export(typed_run_id, artifact_id)
    head = await snapshot_store.get_latest_snapshot(typed_run_id, artifact_id)
    current_snapshot_id = head.snapshot_id if head is not None else None
    stale = await export_store.is_stale(typed_run_id, artifact_id, current_snapshot_id)

    return ExportStatusResponse(
        artifact_id=artifact_id,
        current_snapshot_id=current_snapshot_id,
        latest_export=_to_response(latest_export) if latest_export is not None else None,
        stale=stale,
    )


@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/artifacts/{artifact_id}/export-status/by-format",
    response_model=ExportStatusByFormatResponse,
)
@router.get(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/artifacts/{artifact_id}/export-status/by-format",
    response_model=ExportStatusByFormatResponse,
)
async def get_export_status_by_format(
    run_id: str,
    artifact_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ExportStatusByFormatResponse:
    """Per-format staleness: `/export-status` conflates every format's staleness
    into one flag via whichever row is newest overall, so an artifact with both
    an html and a gift export can show `stale: false` while its gift export is
    actually behind. This checks each exported format independently."""
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)

    export_store = TeachingPackExportStore(session)
    snapshot_store = TeachingPackSnapshotStore(session)
    head = await snapshot_store.get_latest_snapshot(typed_run_id, artifact_id)
    current_snapshot_id = head.snapshot_id if head is not None else None
    existing = await export_store.list_exports(typed_run_id, artifact_id)
    formats = sorted({record.format for record in existing})
    stale_formats = set(
        await export_store.stale_formats(typed_run_id, artifact_id, current_snapshot_id, formats),
    )
    entries: list[FormatStalenessEntry] = []
    for export_format in formats:
        latest = await export_store.get_latest_export_for_format(
            typed_run_id, artifact_id, export_format,
        )
        entries.append(FormatStalenessEntry(
            format=export_format,
            latest_export=_to_response(latest) if latest is not None else None,
            stale=export_format in stale_formats,
        ))
    return ExportStatusByFormatResponse(
        artifact_id=artifact_id, current_snapshot_id=current_snapshot_id, formats=entries,
    )


@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/artifacts/{artifact_id}/exports/regenerate",
    response_model=RegenerateExportsResponse,
)
@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/artifacts/{artifact_id}/exports/regenerate",
    response_model=RegenerateExportsResponse,
)
async def regenerate_exports(
    run_id: str,
    artifact_id: str,
    payload: RegenerateExportsRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> RegenerateExportsResponse:
    """The one explicit re-export trigger in this router (see module docstring):
    a teacher action, never automatic. Only formats that are actually stale get
    a new immutable record; the rest are reused untouched."""
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)

    snapshot_store = TeachingPackSnapshotStore(session)
    head = await snapshot_store.get_latest_snapshot(typed_run_id, artifact_id)
    if head is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")

    formats = payload.formats
    if formats is None:
        existing = await TeachingPackExportStore(session).list_exports(typed_run_id, artifact_id)
        formats = sorted({record.format for record in existing})
    if not formats:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_formats_to_regenerate",
        )

    try:
        result = await regenerate_stale_exports(
            session,
            run_id=typed_run_id,
            artifact_id=artifact_id,
            artifact_type=head.artifact_type,
            head=head,
            formats=formats,
        )
    except UnsupportedExportPairError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "unsupported_export_pair",
                "artifact_type": exc.artifact_type,
                "export_format": exc.export_format,
            },
        ) from exc
    except ExportFormatNotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={"error": "export_format_not_implemented", "export_format": exc.export_format},
        ) from exc
    await session.commit()
    return RegenerateExportsResponse(regenerated=result.regenerated, reused=result.reused)


class TeachingPackBundleExportResponse(BaseModel):
    storage_path: str
    artifact_ids: list[str]


_TEACHING_PACK_BUNDLE_ARTIFACT_ID = "__teaching_pack__"


@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/run/{run_id}/exports/teaching-pack",
    response_model=TeachingPackBundleExportResponse,
)
@router.post(  # pyright: ignore[reportUntypedFunctionDecorator]
    "/runs/{run_id}/exports/teaching-pack",
    response_model=TeachingPackBundleExportResponse,
)
async def export_teaching_pack_bundle(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TeachingPackBundleExportResponse:
    """Bundle every approved artifact in this run into one standalone HTML
    Teaching Pack document (#453, ADR-056) -- distinct from per-artifact
    export above. Always html; not gated by export_manifest_service's
    (artifact_type, format) capability matrix, which answers a different
    question (can *this one artifact* export to *this format*)."""
    typed_run_id = RunId(run_id)
    await get_run_with_ownership(run_id, current_user, session)

    snapshot_store = TeachingPackSnapshotStore(session)
    all_snapshots = await snapshot_store.list_run_snapshots(typed_run_id)
    latest_by_artifact: dict[str, ArtifactSnapshotRead] = {}
    for snapshot in all_snapshots:
        current = latest_by_artifact.get(snapshot.artifact_id)
        if current is None or snapshot.created_at > current.created_at:
            latest_by_artifact[snapshot.artifact_id] = snapshot
    approved = sorted(
        (s for s in latest_by_artifact.values() if s.approved_at is not None),
        key=lambda s: s.artifact_id,
    )
    if not approved:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="no_approved_artifacts",
        )

    first_metadata = (approved[0].content_json or {}).get("metadata")
    metadata = first_metadata if isinstance(first_metadata, dict) else {}
    subject = str(metadata.get("subject", "General"))
    grade_level = str(metadata.get("grade_level", "Grade"))

    writer = TeachingPackBundleWriter()
    storage_path = await writer.write_bundle(
        typed_run_id,
        [
            {
                "artifact_id": s.artifact_id,
                "artifact_type": s.artifact_type,
                "content_json": s.content_json,
            }
            for s in approved
        ],
        title=f"Teaching Pack — {run_id}",
        subject=subject,
        grade_level=grade_level,
    )

    export_store = TeachingPackExportStore(session)
    await export_store.create_export_record(ExportRecordCreate(
        export_id=f"export-{uuid4()}",
        run_id=typed_run_id,
        artifact_id=_TEACHING_PACK_BUNDLE_ARTIFACT_ID,
        # export_records.snapshot_id has a real FK to artifact_snapshots, so a
        # bundle spanning many artifacts can't invent its own id -- it's
        # pinned to one representative constituent snapshot (deterministic:
        # sorted by artifact_id above) rather than tracking the full set.
        snapshot_id=approved[0].snapshot_id,
        format="html",
        storage_path=storage_path,
    ))
    await session.commit()
    return TeachingPackBundleExportResponse(
        storage_path=storage_path,
        artifact_ids=[s.artifact_id for s in approved],
    )
