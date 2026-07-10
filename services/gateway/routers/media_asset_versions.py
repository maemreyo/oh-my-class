"""Immutable, checksummed Media Asset versions and Visual Source Suggestions (#434, ADR-056)."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from common.contracts.media_asset import MediaAssetOwnerScope, MediaAssetVersion
from common.contracts.visual_source_suggestion import VisualSourceSuggestion
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.media_asset_version_store import (
    ChecksumMismatchError,
    MediaAssetHasDependentsError,
    MediaAssetNotFoundError,
    MediaAssetVersionStore,
)
from services.gateway.media_storage import MediaStorage, build_storage_key, sanitize_extension
from services.gateway.routers.teaching_pack_deps import get_run_with_reviewer_access
from services.gateway.teaching_pack_db import TeachingPackSession  # noqa: TC001
from services.gateway.visual_source_suggestion_store import (
    VisualSourceSuggestionNotFoundError,
    VisualSourceSuggestionNotPendingError,
    VisualSourceSuggestionStore,
)

router = APIRouter()

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

_SCOPE_ROLES: dict[str, frozenset[Role]] = {
    "private_teacher": frozenset({Role.TEACHER, Role.ADMIN, Role.SCHOOL_ADMIN, Role.SYSTEM_ADMIN}),
    "organization": frozenset({Role.SCHOOL_ADMIN, Role.SYSTEM_ADMIN}),
    "system": frozenset({Role.SYSTEM_ADMIN}),
}


class ReplaceResponse(BaseModel):
    version: MediaAssetVersion
    impacted_document_ids: list[str]


class RecordDependencyRequest(BaseModel):
    document_id: str = Field(min_length=1, max_length=80)


class CreateVisualSourceSuggestionRequest(BaseModel):
    description: str = Field(min_length=1, max_length=1_000)
    candidate_url: str | None = Field(default=None, max_length=2_000)
    license_hint: str | None = Field(default=None, max_length=500)


class ConvertVisualSourceSuggestionRequest(BaseModel):
    asset_id: str = Field(min_length=1, max_length=80)


class VisualSourceSuggestionListResponse(BaseModel):
    suggestions: list[VisualSourceSuggestion]


@router.post(
    "/media-asset-versions",
    response_model=MediaAssetVersion,
    status_code=status.HTTP_201_CREATED,
)
async def create_media_asset_version(
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
    file: UploadFile = File(...),
    scope: MediaAssetOwnerScope = Form("private_teacher"),
    license_note: str | None = Form(None),
    alt_text: str | None = Form(None),
) -> MediaAssetVersion:
    _require_scope_authority(scope, current_user)
    content = await _read_upload(file)
    asset_id = f"media-{uuid4().hex[:16]}"
    ext = sanitize_extension(file.filename or "")
    storage_key = build_storage_key(current_user.user_id, asset_id, ext)
    MediaStorage().save(storage_key, content)
    version = await MediaAssetVersionStore(session).create(
        asset_id=asset_id,
        owner_scope=scope,
        owner_id=current_user.user_id,
        filename=file.filename or asset_id,
        content_type=file.content_type or "application/octet-stream",
        storage_key=storage_key,
        content=content,
        license_note=license_note,
        alt_text=alt_text,
    )
    await session.commit()
    return version


@router.post(
    "/media-asset-versions/{asset_id}/replace",
    response_model=ReplaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def replace_media_asset_version(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
    file: UploadFile = File(...),
    license_note: str | None = Form(None),
    alt_text: str | None = Form(None),
) -> ReplaceResponse:
    store = MediaAssetVersionStore(session)
    await _require_owned_asset(store, asset_id, current_user)
    content = await _read_upload(file)
    ext = sanitize_extension(file.filename or "")
    storage_key = build_storage_key(current_user.user_id, asset_id, ext)
    MediaStorage().save(storage_key, content)
    try:
        version, impacted = await store.replace(
            asset_id,
            filename=file.filename or asset_id,
            content_type=file.content_type or "application/octet-stream",
            storage_key=storage_key,
            content=content,
            license_note=license_note,
            alt_text=alt_text,
        )
    except MediaAssetNotFoundError as exc:
        raise _media_asset_not_found() from exc
    await session.commit()
    return ReplaceResponse(version=version, impacted_document_ids=impacted)


@router.get("/media-asset-versions/{asset_id}", response_model=MediaAssetVersion)
async def get_media_asset_version(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> MediaAssetVersion:
    store = MediaAssetVersionStore(session)
    return await _require_owned_asset(store, asset_id, current_user)


@router.get("/media-asset-versions/{asset_id}/versions", response_model=list[MediaAssetVersion])
async def list_media_asset_versions(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> list[MediaAssetVersion]:
    store = MediaAssetVersionStore(session)
    await _require_owned_asset(store, asset_id, current_user)
    return await store.list_versions(asset_id)


@router.get("/media-asset-versions/{asset_id}/file")
async def get_media_asset_version_file(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> Response:
    """Streams bytes only after re-verifying the checksum -- the offline-packaging
    integrity guarantee: corrupted/tampered storage never gets served or bundled."""
    store = MediaAssetVersionStore(session)
    version = await _require_owned_asset(store, asset_id, current_user)
    content = MediaStorage().read(version.storage_key)
    try:
        await store.verify_checksum(version.version_id, content)
    except ChecksumMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="checksum_mismatch",
        ) from exc
    return Response(content=content, media_type=version.content_type)


@router.delete("/media-asset-versions/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_asset_version(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> None:
    store = MediaAssetVersionStore(session)
    await _require_owned_asset(store, asset_id, current_user)
    try:
        await store.soft_delete(asset_id)
    except MediaAssetHasDependentsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "media_asset_has_dependents",
                "dependent_document_ids": exc.dependent_document_ids,
            },
        ) from exc
    await session.commit()


@router.post(
    "/media-asset-versions/{asset_id}/dependencies",
    status_code=status.HTTP_201_CREATED,
)
async def record_media_asset_dependency(
    asset_id: str,
    payload: RecordDependencyRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> MediaAssetVersion:
    store = MediaAssetVersionStore(session)
    version = await _require_owned_asset(store, asset_id, current_user)
    await store.record_dependency(version.version_id, payload.document_id)
    await session.commit()
    return version


@router.post(
    "/runs/{run_id}/visual-source-suggestions",
    response_model=VisualSourceSuggestion,
    status_code=status.HTTP_201_CREATED,
)
async def create_visual_source_suggestion(
    run_id: str,
    payload: CreateVisualSourceSuggestionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> VisualSourceSuggestion:
    await get_run_with_reviewer_access(run_id, current_user, session)
    suggestion = await VisualSourceSuggestionStore(session).create(
        run_id=run_id,
        description=payload.description,
        candidate_url=payload.candidate_url,
        license_hint=payload.license_hint,
    )
    await session.commit()
    return suggestion


@router.get(
    "/runs/{run_id}/visual-source-suggestions",
    response_model=VisualSourceSuggestionListResponse,
)
async def list_visual_source_suggestions(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> VisualSourceSuggestionListResponse:
    await get_run_with_reviewer_access(run_id, current_user, session)
    suggestions = await VisualSourceSuggestionStore(session).list_for_run(run_id)
    return VisualSourceSuggestionListResponse(suggestions=suggestions)


@router.post(
    "/visual-source-suggestions/{suggestion_id}/convert",
    response_model=VisualSourceSuggestion,
)
async def convert_visual_source_suggestion(
    suggestion_id: str,
    payload: ConvertVisualSourceSuggestionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> VisualSourceSuggestion:
    """Only ever links an *already-uploaded* Media Asset Version -- this endpoint
    never fetches `candidate_url` itself (ADR-056)."""
    store = MediaAssetVersionStore(session)
    await _require_owned_asset(store, payload.asset_id, current_user)
    suggestion_store = VisualSourceSuggestionStore(session)
    try:
        suggestion = await suggestion_store.convert(suggestion_id, payload.asset_id)
    except VisualSourceSuggestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_source_suggestion_not_found",
        ) from exc
    except VisualSourceSuggestionNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "visual_source_suggestion_not_pending", "status": exc.status},
        ) from exc
    await session.commit()
    return suggestion


@router.post(
    "/visual-source-suggestions/{suggestion_id}/dismiss",
    response_model=VisualSourceSuggestion,
)
async def dismiss_visual_source_suggestion(
    suggestion_id: str,
    current_user: Annotated[User, Depends(require_teacher)],  # noqa: ARG001 -- auth boundary, not row-scoped yet
    session: TeachingPackSession,
) -> VisualSourceSuggestion:
    try:
        suggestion = await VisualSourceSuggestionStore(session).dismiss(suggestion_id)
    except VisualSourceSuggestionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="visual_source_suggestion_not_found",
        ) from exc
    except VisualSourceSuggestionNotPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "visual_source_suggestion_not_pending", "status": exc.status},
        ) from exc
    await session.commit()
    return suggestion


async def _read_upload(file: UploadFile) -> bytes:
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="image_uploads_only",
        )
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="upload_too_large",
        )
    return content


async def _require_owned_asset(
    store: MediaAssetVersionStore, asset_id: str, user: User,
) -> MediaAssetVersion:
    version = await store.get_latest(asset_id)
    if version is None:
        raise _media_asset_not_found()
    if user.role not in {Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN} and version.owner_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not_media_asset_owner")
    return version


def _require_scope_authority(scope: str, user: User) -> None:
    if user.role not in _SCOPE_ROLES[scope]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="scope_requires_higher_authority",
        )


def _media_asset_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="media_asset_not_found")
