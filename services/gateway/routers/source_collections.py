"""Scoped Source Collections API (#432, ADR-051)."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.source_collection import (
    SourceAuthority,
    SourceCollection,
    SourceCollectionEntry,
)
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.routers.teaching_pack_deps import TEACHING_PACK_SESSION
from services.gateway.source_collection_store import (
    SourceCollectionNotFoundError,
    SourceCollectionStore,
)

router = APIRouter()

_SCOPE_ROLES: dict[str, frozenset[Role]] = {
    "private_teacher": frozenset({Role.TEACHER, Role.ADMIN, Role.SCHOOL_ADMIN, Role.SYSTEM_ADMIN}),
    "organization": frozenset({Role.SCHOOL_ADMIN, Role.SYSTEM_ADMIN}),
    "system": frozenset({Role.SYSTEM_ADMIN}),
}


class SourceCollectionEntryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    authority: SourceAuthority
    url: str | None = Field(default=None, max_length=2_000)
    excerpt: str | None = Field(default=None, max_length=8_000)
    subject_key: str | None = Field(default=None, max_length=120)
    claim_value: str | None = Field(default=None, max_length=500)
    copyright_ack: bool = False


class CreateSourceCollectionRequest(BaseModel):
    scope: str = Field(pattern="^(private_teacher|organization|system)$")
    entries: list[SourceCollectionEntryRequest] = Field(min_length=1)


@router.post(
    "/source-collections",
    response_model=SourceCollection,
    status_code=status.HTTP_201_CREATED,
)
async def create_source_collection(
    payload: CreateSourceCollectionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SourceCollection:
    _require_scope_authority(payload.scope, current_user)
    collection = SourceCollection(
        collection_id=f"sources-{uuid4().hex[:16]}",
        scope=payload.scope,  # type: ignore[arg-type]
        owner_id=current_user.user_id,
        entries=[_to_entry(item) for item in payload.entries],
    )
    await SourceCollectionStore(session).create(collection)
    await session.commit()
    return collection


@router.get("/source-collections/{collection_id}", response_model=SourceCollection)
async def get_source_collection(
    collection_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SourceCollection:
    collection = await SourceCollectionStore(session).get(collection_id)
    if collection is None:
        raise _source_collection_not_found()
    _require_read_access(collection, current_user)
    return collection


@router.post(
    "/source-collections/{collection_id}/entries",
    response_model=SourceCollection,
    status_code=status.HTTP_201_CREATED,
)
async def add_source_collection_entry(
    collection_id: str,
    payload: SourceCollectionEntryRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SourceCollection:
    store = SourceCollectionStore(session)
    existing = await store.get(collection_id)
    if existing is None:
        raise _source_collection_not_found()
    _require_read_access(existing, current_user)
    new_entry = _to_entry(payload, entry_id=f"entry-{uuid4().hex[:16]}")
    try:
        updated = await store.add_entry(collection_id, new_entry)
    except SourceCollectionNotFoundError as exc:
        raise _source_collection_not_found() from exc
    await session.commit()
    return updated


def _to_entry(
    payload: SourceCollectionEntryRequest, *, entry_id: str | None = None,
) -> SourceCollectionEntry:
    return SourceCollectionEntry(
        entry_id=entry_id or f"entry-{uuid4().hex[:16]}",
        title=payload.title,
        authority=payload.authority,
        url=payload.url,
        excerpt=payload.excerpt,
        subject_key=payload.subject_key,
        claim_value=payload.claim_value,
        copyright_ack=payload.copyright_ack,
    )


def _require_scope_authority(scope: str, user: User) -> None:
    if user.role not in _SCOPE_ROLES[scope]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="scope_requires_higher_authority",
        )


def _require_read_access(collection: SourceCollection, user: User) -> None:
    if user.role in {Role.SYSTEM_ADMIN, Role.SCHOOL_ADMIN}:
        return
    if collection.scope == "private_teacher" and collection.owner_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_source_collection_owner",
        )


def _source_collection_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="source_collection_not_found",
    )
