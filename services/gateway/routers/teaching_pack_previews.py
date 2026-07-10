from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from common.contracts.artifact import ArtifactContent
from common.contracts.slide_deck import (
    SlideDeckData,
    SlideDeckDisplayPreferences,
    resolve_slide_deck_display_preferences,
)
from packages.agents.slide_deck_engine import UnsupportedTranslationLanguageError, translate_slide_deck
from packages.agents.slide_deck_engine.phases.block_rewrite_llm import (
    BlockRewriteInstructionError,
    generate_slide_deck_block_rewrite,
    resolve_rewrite_instruction,
)
from packages.agents.slide_deck_engine.scoped_block_edit import (
    SlideDeckBlockEditInvalidError,
    SlideDeckBlockNotFoundError,
    apply_scoped_slide_deck_block_edit,
    slide_deck_block_edit_event,
)
from services.gateway.artifact_snapshot_service import produce_artifact_snapshot
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import Role, User  # noqa: TC001
from services.gateway.models import RunStatus
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_snapshot_store import (
    ArtifactSnapshotCreate,
    ArtifactSnapshotRead,
    NonStandaloneSnapshotApprovalError,
    SnapshotBaseVersionConflictError,
    TeachingPackSnapshotStore,
)
from services.gateway.teaching_pack_store import TeachingPackEventCreate, TeachingPackRunStore
from services.gateway.teaching_pack_types import JsonObject, JsonValue, RunId
from services.gateway.routers.teaching_pack_deps import get_run_with_ownership
from services.gateway.routers.teaching_pack_preview_schemas import (
    ArtifactVersionListResponse,
    ArtifactVersionSummary,
    RenderedSnapshotMetadataResponse,
    RestoreArtifactVersionRequest,
    RestoreArtifactVersionResponse,
    SlideDeckBlockEditRequest,
    SlideDeckBlockEditResponse,
    SlideDeckBlockRewriteSuggestionRequest,
    SlideDeckBlockRewriteSuggestionResponse,
    SnapshotApprovalRequest,
    SnapshotApprovalResponse,
    TranslateSlideDeckRequest,
    TranslateSlideDeckResponse,
)
from services.gateway.renderer_adapter import render_artifact_content

router = APIRouter()
TEACHING_PACK_SESSION = Depends(get_teaching_pack_session)
PREVIEW_SECURITY_HEADERS = {
    "X-Frame-Options": "SAMEORIGIN",
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data:",
}


@router.get(
    "/run/{run_id}/snapshots/{snapshot_id}",
    response_model=RenderedSnapshotMetadataResponse,
)
@router.get(
    "/runs/{run_id}/snapshots/{snapshot_id}",
    response_model=RenderedSnapshotMetadataResponse,
)
async def get_rendered_snapshot_metadata(
    run_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> RenderedSnapshotMetadataResponse:
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    return _metadata_response(snapshot)


@router.get("/run/{run_id}/snapshots/{snapshot_id}/preview")
@router.get("/runs/{run_id}/snapshots/{snapshot_id}/preview")
async def preview_rendered_snapshot(
    run_id: str,
    snapshot_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    view: Annotated[
        Literal["student", "teacher", "print"],
        Query(),
    ] = "student",
    # ADR-043 (SDH-04): the app's Print & sharing panel sends the full typed
    # SlideDeckDisplayPreferences shape via `surface` instead of the legacy
    # single `view` value. Left loose (not `SlideDeckDisplaySurface`) and
    # resolved through `resolve_slide_deck_display_preferences` below so a
    # malformed value degrades safely instead of 422ing the preview -- the
    # same resilience `_print_preview_html` already gives untrusted stored
    # preferences. Omitting `surface` entirely preserves the legacy `view`
    # behavior byte-for-byte for existing callers (e.g. the generic
    # multi-artifact-type preview in `ContentSnapshots`).
    surface: Annotated[str | None, Query()] = None,
    print_layout: Annotated[str | None, Query()] = None,
    slides_per_page: Annotated[int | None, Query()] = None,
    chrome: Annotated[str | None, Query()] = None,
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> HTMLResponse:
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")

    if surface is not None:
        preferences = resolve_slide_deck_display_preferences({
            "surface": surface,
            "print_layout": print_layout,
            "slides_per_page": slides_per_page,
            "chrome": chrome,
        })
        if preferences.surface in ("teacher", "print", "review") and current_user.role not in (Role.TEACHER, Role.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="teacher_preview_required",
            )
        if preferences.surface == "print":
            html = await _slide_deck_preview_html_for_preferences(snapshot, preferences)
        elif preferences.surface in ("teacher", "review"):
            html = snapshot.rendered_html
        else:
            html = snapshot.student_rendered_html
        return HTMLResponse(content=html, headers=PREVIEW_SECURITY_HEADERS)

    if view in ("teacher", "print") and current_user.role not in (Role.TEACHER, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="teacher_preview_required",
        )
    if view == "print":
        html = await _print_preview_html(snapshot)
    else:
        html = snapshot.rendered_html if view == "teacher" else snapshot.student_rendered_html
    return HTMLResponse(content=html, headers=PREVIEW_SECURITY_HEADERS)


@router.post(
    "/run/{run_id}/approved-snapshots",
    response_model=SnapshotApprovalResponse,
)
@router.post(
    "/runs/{run_id}/approved-snapshots",
    response_model=SnapshotApprovalResponse,
)
async def approve_rendered_snapshots(
    run_id: str,
    payload: SnapshotApprovalRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SnapshotApprovalResponse:
    typed_run_id = RunId(run_id)
    run_status = await _require_run_access(session, typed_run_id, current_user)
    if run_status is not RunStatus.AWAITING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="run_not_awaiting_approval",
        )
    snapshot_ids = list(dict.fromkeys(payload.snapshot_ids))
    snapshot_store = TeachingPackSnapshotStore(session)
    try:
        approved_count = await snapshot_store.approve_snapshots(typed_run_id, snapshot_ids)
    except NonStandaloneSnapshotApprovalError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="non_standalone_snapshot",
        ) from exc
    if approved_count != len(snapshot_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    event_snapshot_ids: list[JsonValue] = list(snapshot_ids)
    event_payload: JsonObject = {"snapshot_ids": event_snapshot_ids}
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name="teaching_pack.content.approved_snapshots",
        visibility=TeachingPackEventVisibility.TEACHER,
        payload=event_payload,
    ))
    await session.commit()
    return SnapshotApprovalResponse(run_id=run_id, approved_snapshot_ids=snapshot_ids)


@router.post(
    "/run/{run_id}/snapshots/{snapshot_id}/translate",
    response_model=TranslateSlideDeckResponse,
)
@router.post(
    "/runs/{run_id}/snapshots/{snapshot_id}/translate",
    response_model=TranslateSlideDeckResponse,
)
async def translate_slide_deck_snapshot(
    run_id: str,
    snapshot_id: str,
    payload: TranslateSlideDeckRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> TranslateSlideDeckResponse:
    """SDX-01: "Dịch deck này" -- translate a slide_deck snapshot into a new,
    independent snapshot/deck, never overwriting the source."""
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot = await TeachingPackSnapshotStore(session).get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    if snapshot.artifact_type != "slide_deck":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_a_slide_deck")
    deck_dict = _slide_deck_data(snapshot)
    if deck_dict is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_data_missing")

    try:
        deck = SlideDeckData.model_validate(deck_dict)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_data_invalid") from exc

    try:
        translated = await translate_slide_deck(
            deck,
            run_id=run_id,
            target_language=payload.target_language,
            source_snapshot_id=snapshot_id,
        )
    except UnsupportedTranslationLanguageError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_target_language") from exc

    translated_artifact = _translated_artifact_content(translated)
    new_snapshot_id = await produce_artifact_snapshot(
        session,
        run_id=typed_run_id,
        artifact_content=translated_artifact,
        artifact_type="slide_deck",
        renderer_version=snapshot.renderer_version,
        template_version=snapshot.template_version,
        theme_version=snapshot.theme_version,
    )
    await session.commit()
    return TranslateSlideDeckResponse(
        run_id=run_id,
        source_snapshot_id=snapshot_id,
        snapshot_id=new_snapshot_id,
        deck_id=translated.deck_id,
    )


@router.patch(
    "/run/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}",
    response_model=SlideDeckBlockEditResponse,
)
@router.patch(
    "/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}",
    response_model=SlideDeckBlockEditResponse,
)
async def edit_slide_deck_snapshot_block(
    run_id: str,
    snapshot_id: str,
    block_id: str,
    payload: SlideDeckBlockEditRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SlideDeckBlockEditResponse:
    """SDE-04: standalone scoped block edit -- works against any snapshot the
    requesting teacher owns, independent of the run's current graph/gate
    state (unlike the gate-resume `action: "edit"` path, which only applies
    while the content_approval gate is open). Optimistic locking: 409 if
    `base_snapshot_id` isn't the artifact's current head.

    `snapshot_id` in the URL only needs to identify *which artifact* is being
    edited -- the edit always applies to that artifact's current head
    (resolved fresh via `get_latest_snapshot`), never to a stale copy of the
    URL's own snapshot.
    """
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot_store = TeachingPackSnapshotStore(session)
    snapshot = await snapshot_store.get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    if snapshot.artifact_type != "slide_deck":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_a_slide_deck")

    head = await snapshot_store.get_latest_snapshot(typed_run_id, snapshot.artifact_id)
    if head is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    deck_dict = _slide_deck_data(head)
    if deck_dict is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_data_missing")

    try:
        deck = SlideDeckData.model_validate(deck_dict)
        updated_deck = apply_scoped_slide_deck_block_edit(deck, block_id, payload.new_content)
    except SlideDeckBlockNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block_not_found") from exc
    except (SlideDeckBlockEditInvalidError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_edit") from exc

    edited_artifact = _edited_artifact_content(head, updated_deck)
    rendered_html = await render_artifact_content(edited_artifact)
    new_snapshot_id = f"snapshot-{uuid4().hex[:12]}"
    try:
        created = await snapshot_store.create_scoped_edit_snapshot(
            run_id=typed_run_id,
            artifact_id=head.artifact_id,
            base_snapshot_id=payload.base_snapshot_id,
            new_snapshot=ArtifactSnapshotCreate(
                snapshot_id=new_snapshot_id,
                run_id=typed_run_id,
                artifact_id=head.artifact_id,
                artifact_type="slide_deck",
                content_json=edited_artifact,
                rendered_html=rendered_html,
                renderer_version=head.renderer_version,
                template_version=head.template_version,
                theme_version=head.theme_version,
                version_mismatch_policy="warn",
            ),
        )
    except SnapshotBaseVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="base_snapshot_id_stale") from exc

    edit_event = slide_deck_block_edit_event(
        head.artifact_id, block_id, payload.rationale, authority=payload.authority, snapshot_id=created.snapshot_id,
    )
    edit_event_payload = edit_event["payload"]
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name=str(edit_event["event_name"]),
        visibility=TeachingPackEventVisibility.TEACHER,
        payload=edit_event_payload if isinstance(edit_event_payload, dict) else {},
    ))
    await session.commit()
    return SlideDeckBlockEditResponse(
        run_id=run_id,
        artifact_id=head.artifact_id,
        block_id=block_id,
        base_snapshot_id=payload.base_snapshot_id,
        snapshot_id=created.snapshot_id,
    )


@router.post(
    "/run/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}/rewrite-suggestion",
    response_model=SlideDeckBlockRewriteSuggestionResponse,
)
@router.post(
    "/runs/{run_id}/snapshots/{snapshot_id}/blocks/{block_id}/rewrite-suggestion",
    response_model=SlideDeckBlockRewriteSuggestionResponse,
)
async def suggest_slide_deck_block_rewrite(
    run_id: str,
    snapshot_id: str,
    block_id: str,
    payload: SlideDeckBlockRewriteSuggestionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> SlideDeckBlockRewriteSuggestionResponse:
    """SDE-08: AI-assisted rewrite CANDIDATE for one block -- returns a
    before/after pair for the teacher's confirmation modal. Never persists
    anything; the teacher's own "Apply" click, which reuses
    `edit_slide_deck_snapshot_block` with `authority="ai_assisted_edit"`, is
    the only path that writes a new snapshot/event.

    Resolves the artifact's current head the same way the block-edit endpoint
    does (`get_latest_snapshot`, not the URL's own possibly-stale
    `snapshot_id`), so the candidate is always generated against the latest
    body, not a stale copy.
    """
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot_store = TeachingPackSnapshotStore(session)
    snapshot = await snapshot_store.get_snapshot(typed_run_id, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    if snapshot.artifact_type != "slide_deck":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="not_a_slide_deck")

    head = await snapshot_store.get_latest_snapshot(typed_run_id, snapshot.artifact_id)
    if head is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    deck_dict = _slide_deck_data(head)
    if deck_dict is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_data_missing")

    try:
        deck = SlideDeckData.model_validate(deck_dict)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="slide_deck_data_invalid") from exc

    current_body = next(
        (block.body for slide in deck.slides for block in slide.blocks if block.block_id == block_id),
        None,
    )
    if current_body is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="block_not_found")

    try:
        instruction = resolve_rewrite_instruction(preset=payload.preset, freeform=payload.instruction)
    except BlockRewriteInstructionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    rewritten = await generate_slide_deck_block_rewrite(
        run_id=run_id, current_body=current_body, instruction=instruction,
    )
    if rewritten is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="rewrite_unavailable")

    return SlideDeckBlockRewriteSuggestionResponse(block_id=block_id, before=current_body, after=rewritten)


_CONTENT_VERSION_EVENT_NAME = "teaching_pack.content_version.created"
_MAX_VERSION_LABEL_RATIONALE_LEN = 60


@router.get(
    "/run/{run_id}/artifacts/{artifact_id}/versions",
    response_model=ArtifactVersionListResponse,
)
@router.get(
    "/runs/{run_id}/artifacts/{artifact_id}/versions",
    response_model=ArtifactVersionListResponse,
)
async def list_artifact_versions(
    run_id: str,
    artifact_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> ArtifactVersionListResponse:
    """SDE-05: linear, newest-first, paginated version history for one artifact.

    Not a diff/comparison view (explicitly deferred, ADR-047 decision 7) --
    just enough per version to identify it (timestamp, who/what produced it,
    a short label) and open it read-only via the existing
    `GET .../snapshots/{snapshot_id}/preview` endpoint.
    """
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot_store = TeachingPackSnapshotStore(session)
    page, total = await snapshot_store.list_artifact_snapshot_versions(
        typed_run_id, artifact_id, limit=limit, offset=offset,
    )
    if total == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artifact_not_found")
    earliest_snapshot_id = await snapshot_store.get_earliest_snapshot_id(typed_run_id, artifact_id)
    head = await snapshot_store.get_latest_snapshot(typed_run_id, artifact_id)
    events_by_snapshot_id = await _content_version_events_by_snapshot_id(session, typed_run_id, artifact_id)
    versions = [
        ArtifactVersionSummary(
            snapshot_id=snapshot.snapshot_id,
            created_at=snapshot.created_at,
            authority=_version_authority(snapshot, earliest_snapshot_id, events_by_snapshot_id),
            label=_version_label(snapshot, earliest_snapshot_id, events_by_snapshot_id),
            is_current=head is not None and snapshot.snapshot_id == head.snapshot_id,
        )
        for snapshot in page
    ]
    return ArtifactVersionListResponse(
        run_id=run_id,
        artifact_id=artifact_id,
        total=total,
        limit=limit,
        offset=offset,
        versions=versions,
    )


@router.post(
    "/run/{run_id}/artifacts/{artifact_id}/versions/{version_snapshot_id}/restore",
    response_model=RestoreArtifactVersionResponse,
)
@router.post(
    "/runs/{run_id}/artifacts/{artifact_id}/versions/{version_snapshot_id}/restore",
    response_model=RestoreArtifactVersionResponse,
)
async def restore_artifact_version(
    run_id: str,
    artifact_id: str,
    version_snapshot_id: str,
    payload: RestoreArtifactVersionRequest,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
) -> RestoreArtifactVersionResponse:
    """SDE-05: "Restore this version" -- copies an old version's content into
    a brand-new snapshot row. Never mutates or deletes the restored version
    or any version in between; this only ever inserts a new row. Reuses the
    same optimistic-locked `create_scoped_edit_snapshot` path as a normal
    block edit, so a stale `base_snapshot_id` 409s exactly like SDE-04's
    edit endpoint instead of silently clobbering a newer head.
    """
    typed_run_id = RunId(run_id)
    await _require_run_access(session, typed_run_id, current_user)
    snapshot_store = TeachingPackSnapshotStore(session)
    restore_from = await snapshot_store.get_snapshot(typed_run_id, version_snapshot_id)
    if restore_from is None or restore_from.artifact_id != artifact_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="snapshot_not_found")
    if restore_from.content_json is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="snapshot_content_missing")

    new_snapshot_id = f"snapshot-{uuid4().hex[:12]}"
    try:
        created = await snapshot_store.create_scoped_edit_snapshot(
            run_id=typed_run_id,
            artifact_id=artifact_id,
            base_snapshot_id=payload.base_snapshot_id,
            new_snapshot=ArtifactSnapshotCreate(
                snapshot_id=new_snapshot_id,
                run_id=typed_run_id,
                artifact_id=artifact_id,
                artifact_type=restore_from.artifact_type,
                content_json=_restored_content(restore_from),
                rendered_html=restore_from.rendered_html,
                student_rendered_html=restore_from.student_rendered_html,
                renderer_version=restore_from.renderer_version,
                template_version=restore_from.template_version,
                theme_version=restore_from.theme_version,
                version_mismatch_policy="warn",
            ),
        )
    except SnapshotBaseVersionConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="base_snapshot_id_stale") from exc

    restore_event: JsonObject = {
        "artifact_id": artifact_id,
        "authority": "teacher_edit",
        "snapshot_id": created.snapshot_id,
        "diff": {
            "status": "restore",
            "restored_from_snapshot_id": restore_from.snapshot_id,
        },
    }
    await TeachingPackRunStore(session).write_event(TeachingPackEventCreate(
        run_id=typed_run_id,
        event_name=_CONTENT_VERSION_EVENT_NAME,
        visibility=TeachingPackEventVisibility.TEACHER,
        payload=restore_event,
    ))
    await session.commit()
    return RestoreArtifactVersionResponse(
        run_id=run_id,
        artifact_id=artifact_id,
        restored_from_snapshot_id=restore_from.snapshot_id,
        base_snapshot_id=payload.base_snapshot_id,
        snapshot_id=created.snapshot_id,
    )


def _restored_content(snapshot: ArtifactSnapshotRead) -> JsonObject:
    """Copy a past version's content_json verbatim for a restore, tagging
    provenance (+ a timestamp) into `metadata`. The tag also guarantees the
    new row's content_hash differs from the restored row's -- `content_hash`
    has a *global* uniqueness constraint (`ArtifactSnapshot.content_hash`),
    so an untagged byte-for-byte copy would collide and `create_snapshot`
    would silently return the *old* row instead of inserting a new one
    (defeating "restore creates a brand-new version").
    """
    content = dict(snapshot.content_json or {})
    metadata = content.get("metadata")
    content["metadata"] = {
        **(metadata if isinstance(metadata, dict) else {}),
        "restored_from_snapshot_id": snapshot.snapshot_id,
        "restored_at": datetime.now(UTC).isoformat(),
    }
    return content


async def _content_version_events_by_snapshot_id(
    session: AsyncSession,
    run_id: RunId,
    artifact_id: str,
) -> dict[str, JsonObject]:
    """Map `snapshot_id -> content_version.created event payload` for one
    artifact, so the version list can label each row without guessing by
    timestamp order. Events pre-dating SDE-05 (or from the gate-resume edit
    path, which has no snapshot row at event-write time) never carried a
    `snapshot_id` and are simply absent here -- callers fall back to a
    generic label for those.
    """
    events = await TeachingPackRunStore(session).list_events_by_name(run_id, _CONTENT_VERSION_EVENT_NAME)
    events_by_snapshot_id: dict[str, JsonObject] = {}
    for event in events:
        payload = event.payload
        if not isinstance(payload, dict) or payload.get("artifact_id") != artifact_id:
            continue
        event_snapshot_id = payload.get("snapshot_id")
        if isinstance(event_snapshot_id, str):
            events_by_snapshot_id[event_snapshot_id] = payload
    return events_by_snapshot_id


def _version_authority(
    snapshot: ArtifactSnapshotRead,
    earliest_snapshot_id: str | None,
    events_by_snapshot_id: dict[str, JsonObject],
) -> str:
    if snapshot.snapshot_id == earliest_snapshot_id:
        return "initial"
    event_payload = events_by_snapshot_id.get(snapshot.snapshot_id)
    authority = event_payload.get("authority") if event_payload is not None else None
    return authority if isinstance(authority, str) else "teacher_edit"


def _version_label(
    snapshot: ArtifactSnapshotRead,
    earliest_snapshot_id: str | None,
    events_by_snapshot_id: dict[str, JsonObject],
) -> str:
    if snapshot.snapshot_id == earliest_snapshot_id:
        return "Initial version"
    event_payload = events_by_snapshot_id.get(snapshot.snapshot_id)
    if event_payload is None:
        return "Manual edit"
    diff = event_payload.get("diff")
    diff = diff if isinstance(diff, dict) else {}
    if diff.get("status") == "restore":
        return "Restored version"
    rationale = diff.get("rationale")
    rationale = rationale.strip() if isinstance(rationale, str) and rationale.strip() else None
    if event_payload.get("authority") == "ai_assisted_edit":
        return f"AI rewrite: {_truncate(rationale)}" if rationale else "AI rewrite"
    return "Manual edit"


def _truncate(text: str, *, limit: int = _MAX_VERSION_LABEL_RATIONALE_LEN) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _edited_artifact_content(snapshot: ArtifactSnapshotRead, deck: SlideDeckData) -> JsonObject:
    # Unlike `_translated_artifact_content` (which builds a fresh
    # `ArtifactContent`), a block edit must preserve the source snapshot's
    # own title/theme/accessibility/metadata untouched -- only the deck
    # payload embedded twice (`metadata.slide_deck_data` and
    # `sections[0].slide_deck`, per `build_slide_deck_artifact`'s shape)
    # changes.
    deck_data = deck.model_dump(mode="json")
    content = dict(snapshot.content_json or {})
    metadata = content.get("metadata")
    content["metadata"] = {**(metadata if isinstance(metadata, dict) else {}), "slide_deck_data": deck_data}
    sections = content.get("sections")
    if isinstance(sections, list) and sections and isinstance(sections[0], dict):
        content["sections"] = [{**sections[0], "slide_deck": deck_data}, *sections[1:]]
    return content


def _slide_deck_data(snapshot: ArtifactSnapshotRead) -> JsonObject | None:
    metadata = snapshot.content_json.get("metadata")
    if not isinstance(metadata, dict):
        return None
    deck = metadata.get("slide_deck_data")
    return deck if isinstance(deck, dict) else None


def _translated_artifact_content(deck: SlideDeckData) -> JsonObject:
    # Mirrors `build_slide_deck_artifact`'s ArtifactContent shape (title,
    # sections, metadata.slide_deck_data) so the translated snapshot renders
    # through the exact same slide-deck renderer path as any other deck.
    deck_data = deck.model_dump(mode="json")
    artifact = ArtifactContent(
        artifact_type="slide_deck",
        theme=deck.theme,
        title=deck.title,
        sections=[{"title": deck.title, "slide_deck": deck_data}],
        metadata={
            "generation_mode": "slide_deck_translation",
            "artifact_type": "slide_deck",
            "slide_deck_data": deck_data,
        },
        accessibility={"language": deck.accessibility.language},
    )
    return artifact.model_dump()


async def _require_run_access(session: AsyncSession, run_id: RunId, user: User) -> RunStatus:
    run = await get_run_with_ownership(run_id, user, session)
    return run.status


def _metadata_response(snapshot: ArtifactSnapshotRead) -> RenderedSnapshotMetadataResponse:
    return RenderedSnapshotMetadataResponse(
        snapshot_id=snapshot.snapshot_id,
        artifact_id=snapshot.artifact_id,
        artifact_type=snapshot.artifact_type,
        content_hash=snapshot.content_hash,
        html_hash=snapshot.html_hash,
        renderer_version=snapshot.renderer_version,
        template_version=snapshot.template_version,
        theme_version=snapshot.theme_version,
        standalone_valid=snapshot.standalone_valid,
        approved_at=snapshot.approved_at,
    )


async def _print_preview_html(snapshot: ArtifactSnapshotRead) -> str:
    if snapshot.artifact_type != "slide_deck":
        return snapshot.rendered_html
    content = {**snapshot.content_json, "artifact_type": snapshot.artifact_type}
    metadata = content.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("slide_deck_data"), dict):
        deck = dict(metadata["slide_deck_data"])
        deck["render_surface"] = "print"
        deck["display_preferences"] = _effective_print_display_preferences(deck).model_dump()
        content["metadata"] = {**metadata, "slide_deck_data": deck}
    else:
        content["render_surface"] = "print"
    return await render_artifact_content(content)


def _effective_print_display_preferences(deck: JsonObject) -> SlideDeckDisplayPreferences:
    """Merge a deck's own (possibly absent) preferences with the print override.

    Old snapshots never had a ``display_preferences`` field; the resolver
    falls back to production-safe defaults per-field, so print preview
    never breaks on artifacts predating this contract.
    """
    existing = deck.get("display_preferences")
    base = existing if isinstance(existing, dict) else {}
    return resolve_slide_deck_display_preferences({**base, "surface": "print"})


async def _slide_deck_preview_html_for_preferences(
    snapshot: ArtifactSnapshotRead,
    preferences: SlideDeckDisplayPreferences,
) -> str:
    """ADR-043 typed seam (SDH-04): live-render a slide-deck print preview
    for a fully-resolved, explicit preference request from the app's Print
    & sharing panel. Unlike ``_effective_print_display_preferences`` (which
    merges with whatever the deck itself stored), the caller's request is
    the source of truth here -- the teacher explicitly chose these options
    in the UI, so they always win outright.
    """
    if snapshot.artifact_type != "slide_deck":
        return snapshot.rendered_html
    content = {**snapshot.content_json, "artifact_type": snapshot.artifact_type}
    metadata = content.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("slide_deck_data"), dict):
        deck = dict(metadata["slide_deck_data"])
        deck["render_surface"] = preferences.surface
        deck["display_preferences"] = preferences.model_dump()
        content["metadata"] = {**metadata, "slide_deck_data": deck}
    else:
        content["render_surface"] = preferences.surface
    return await render_artifact_content(content)
