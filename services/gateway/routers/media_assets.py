"""Teacher-scoped media asset library (SDX-02).

Upload once, reuse the same image/diagram across any deck the uploading
teacher owns. See ``media_asset_store.py`` for the ownership model and
``media_storage.py`` for the flat, teacher-scoped storage key scheme.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - Pydantic resolves the response field at runtime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import (
    User,  # noqa: TC001  needed at runtime for dependency injection
)
from services.gateway.exceptions import NotFoundError, ValidationError
from services.gateway.media_alt_text_llm import generate_alt_text_for_image
from services.gateway.media_asset_store import MediaAssetStore
from services.gateway.media_storage import MediaStorage, build_storage_key, sanitize_extension
from services.gateway.teaching_pack_db import (
    TeachingPackSession,  # noqa: TC001  needed at runtime for DI
)

router = APIRouter(prefix="/media-assets", tags=["media-assets"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB — images/diagrams only, not video


class MediaAssetResponse(BaseModel):
    asset_id: str
    filename: str
    content_type: str
    tags: list[str]
    alt_text: str | None
    storage_key: str
    created_at: datetime


class GenerateAltTextResponse(BaseModel):
    """A candidate the teacher must Accept/Reject in the confirmation modal
    (SDX-04) — never persisted by this endpoint alone."""

    candidate: str


class SetAltTextRequest(BaseModel):
    """Mirrors `SlideDeckMedia.alt_text`'s schema constraint
    (`common/contracts/slide_deck.py`) so a rejected/oversized value 422s
    here rather than reaching the deck contract later."""

    alt_text: str = Field(min_length=1, max_length=500)


def _to_response(row) -> MediaAssetResponse:  # noqa: ANN001
    return MediaAssetResponse(
        asset_id=row.asset_id,
        filename=row.filename,
        content_type=row.content_type,
        tags=row.tags,
        alt_text=row.alt_text,
        storage_key=row.storage_key,
        created_at=row.created_at,
    )


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


@router.post("")  # pyright: ignore[reportUntypedFunctionDecorator]
async def upload_media_asset(
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
    file: UploadFile = File(...),
    tags: str = Form(""),
    alt_text: str | None = Form(None),
) -> MediaAssetResponse:
    if not (file.content_type or "").startswith("image/"):
        raise ValidationError(message="Only image/diagram uploads are supported")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        limit_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise ValidationError(message=f"File exceeds the {limit_mb}MB upload limit")

    asset_id = f"media-{uuid4().hex}"
    ext = sanitize_extension(file.filename or "")
    storage_key = build_storage_key(current_user.user_id, asset_id, ext)

    MediaStorage().save(storage_key, content)

    store = MediaAssetStore(session)
    row = await store.create_asset(
        asset_id=asset_id,
        teacher_id=current_user.user_id,
        filename=file.filename or asset_id,
        content_type=file.content_type or "application/octet-stream",
        storage_key=storage_key,
        tags=_parse_tags(tags),
        alt_text=alt_text,
    )
    await session.commit()
    return _to_response(row)


@router.get("")  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_media_assets(
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
    q: str | None = None,
    tag: str | None = None,
) -> list[MediaAssetResponse]:
    store = MediaAssetStore(session)
    rows = await store.list_assets(current_user.user_id, q=q, tag=tag)
    return [_to_response(row) for row in rows]


@router.get("/{asset_id}/file")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_media_asset_file(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> Response:
    store = MediaAssetStore(session)
    row = await store.get_asset(asset_id, current_user.user_id)
    if row is None:
        raise NotFoundError(message=f"Media asset {asset_id} not found")
    content = MediaStorage().read(row.storage_key)
    return Response(content=content, media_type=row.content_type)


@router.post("/{asset_id}/generate-alt-text")  # pyright: ignore[reportUntypedFunctionDecorator]
async def generate_media_asset_alt_text(
    asset_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
    context: str | None = None,
) -> GenerateAltTextResponse:
    """SDX-04: returns a best-guess alt-text candidate for the teacher's
    before/after confirmation modal. Never persisted here — see
    `set_media_asset_alt_text` for the Accept step. No vision capability
    exists in this LLM setup (see `media_alt_text_llm.py`'s docstring), so
    the candidate is built from the asset's filename/tags/optional slide
    context, not true image understanding."""
    store = MediaAssetStore(session)
    row = await store.get_asset(asset_id, current_user.user_id)
    if row is None:
        raise NotFoundError(message=f"Media asset {asset_id} not found")
    candidate = await generate_alt_text_for_image(
        run_id=f"media-alt-text-{asset_id}",
        filename=row.filename,
        tags=row.tags,
        context=context,
    )
    if candidate is None:
        raise ValidationError(message="Alt-text generation failed — try again")
    return GenerateAltTextResponse(candidate=candidate)


@router.put("/{asset_id}/alt-text")  # pyright: ignore[reportUntypedFunctionDecorator]
async def set_media_asset_alt_text(
    asset_id: str,
    body: SetAltTextRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: TeachingPackSession,
) -> MediaAssetResponse:
    """Persists alt text the teacher Accepted (AI-generated or hand-edited).
    `SetAltTextRequest.alt_text`'s Pydantic `Field(min_length=1,
    max_length=500)` already enforces the same schema constraint
    `SlideDeckMedia.alt_text` needs downstream — a bad value 422s before it
    reaches the store."""
    store = MediaAssetStore(session)
    row = await store.set_alt_text(asset_id, current_user.user_id, body.alt_text)
    if row is None:
        raise NotFoundError(message=f"Media asset {asset_id} not found")
    await session.commit()
    return _to_response(row)
