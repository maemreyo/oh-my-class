"""Live TeachingSession sync routes (TSP-03): the real callers of the event
log / Redis Pub/Sub code in `teaching_session/event_log.py` and
`teaching_session/live_sync.py`.

This is the first live router for `teaching_session/` -- TSP-01/TSP-02 built
the data model, retention policy, and join/token issuance, but wired no HTTP
routes (see `teaching_session/session_auth.py`'s docstring). Every route here
is gated by a session-role token (`require_controller`/`require_session_role`
from `session_auth.py`, never the account JWT the rest of the gateway uses)
and is exempted from `JWTMiddleware` accordingly -- see
`middleware/auth_middleware.py::PUBLIC_PREFIXES`.

Transport policy (base AC3): SSE broadcast (`/stream`) + REST POST actions
(`/slide`, `/responses`) + polling fallback (`/state`, or `/stream` itself
degrading to a poll loop if Redis is unreachable). WebSocket is deferred.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import uuid4

import anyio
import orjson
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from packages.agents.slide_deck_engine.phases.block_rewrite_llm import (
    BlockRewriteInstructionError,
    generate_slide_deck_block_rewrite,
    resolve_rewrite_instruction,
)
from packages.agents.teaching_pack.teacher_memory import (
    read_pacing_nudge_preference,
    write_pacing_nudge_preference,
)
from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.teaching_pack_db import get_teaching_pack_session
from services.gateway.teaching_session import live_sync
from services.gateway.teaching_session.branches import (
    BranchContentType,
    BranchRejected,
    BranchSource,
    create_precomputed_branch,
    list_precomputed_branches,
)
from services.gateway.teaching_session.event_log import (
    RecordedEvent,
    current_state,
    find_by_idempotency_key,
    lock_session_events,
    record_event,
    replay_events,
    row_to_event,
)
from services.gateway.teaching_session.events import (
    SessionEvent,
    SessionEventType,
    SessionReadModel,
)
from services.gateway.teaching_session.models import SessionDataCategory, TeachingSession
from services.gateway.teaching_session.responses import (
    ResponseKind,
    ResponseRejected,
    get_session_aggregates,
    record_response,
)
from services.gateway.teaching_session.retention import allowed_data_categories_for_tier
from services.gateway.teaching_session.session_auth import (
    get_session_claims,
    get_session_claims_for_stream,
    require_controller,
    require_session_role,
)
from services.gateway.teaching_session.tokens import SessionRole, SessionTokenPayload  # noqa: TC001

router = APIRouter()

_POLL_INTERVAL_SECONDS = 2.0


class AdvanceSlideRequest(BaseModel):
    slide_id: str
    slide_index: int | None = None


class SelectBranchRequest(BaseModel):
    slide_id: str
    branch_id: str


class PrecomputedBranchResponse(BaseModel):
    """One zero-latency branch option (TSP-06 amendment #2: the cockpit's default)."""

    branch_id: str
    slide_id: str
    interaction_id: str | None
    branch_type: BranchContentType
    label: str


class ListPrecomputedBranchesResponse(BaseModel):
    branches: list[PrecomputedBranchResponse]


class BranchSuggestionRequest(BaseModel):
    """TSP-06 amendment #1: identical shape to SDE-08's rewrite-suggestion
    request -- exactly one of `preset`/`instruction`, resolved by the same
    `resolve_rewrite_instruction` function. Never persists."""

    slide_id: str
    current_body: str = Field(min_length=1, max_length=2000)
    preset: str | None = None
    instruction: str | None = Field(default=None, max_length=500)


class BranchSuggestionResponse(BaseModel):
    """Handed straight back to the requesting teacher's own HTTP response --
    never written anywhere, never broadcast (see `branches.py` module
    docstring's content-safety-boundary note)."""

    slide_id: str
    before: str
    after: str


class ApplyBranchSuggestionRequest(BaseModel):
    """The teacher's explicit "Apply" on the reused `AiBlockRewriteConfirmModal`
    (SDE-08's exact modal). `approved_body` is that modal's `after` text,
    possibly re-edited by the teacher before applying -- either way it is
    re-validated by the same quality gate a precomputed branch must pass
    before it can ever land in `branch_selected`."""

    slide_id: str
    branch_type: BranchContentType
    label: str = Field(min_length=1, max_length=200)
    approved_body: str = Field(min_length=1, max_length=2000)
    interaction_id: str | None = None


class SubmitResponseRequest(BaseModel):
    """One student response. Persistence/PII/retention-tier gating is TSP-05's
    `responses.record_response` -- this route's job is only to call that with
    the right session context, then log the resulting aggregate as a
    significant `aggregate_updated` event for live broadcast (this route
    never writes `SessionStudentResponse`/`SessionResponseAggregate` itself).

    `interaction_allows_free_text`/`session_allows_free_text` default closed
    (deny free text) -- neither the interaction-authoring policy nor the
    session-level free-text toggle has a lookup wired yet (SDTF-01/SDE-*
    territory), so a caller must explicitly assert both are allowed.
    """

    interaction_id: str
    kind: ResponseKind
    payload: dict[str, Any]
    kc_ids: list[str] | None = None
    correct: bool | None = None
    interaction_allows_free_text: bool = False
    session_allows_free_text: bool = False


class SessionStateResponse(BaseModel):
    session_id: str
    current_slide_id: str | None
    current_branch_id: str | None
    open_interaction_id: str | None
    tallies: dict[str, dict[str, int]]
    ended: bool
    last_sequence: int


def _to_state_response(state: SessionReadModel) -> SessionStateResponse:
    return SessionStateResponse(
        session_id=state.session_id,
        current_slide_id=state.current_slide_id,
        current_branch_id=state.current_branch_id,
        open_interaction_id=state.open_interaction_id,
        tallies=state.tallies,
        ended=state.ended,
        last_sequence=state.last_sequence,
    )


async def _load_session_or_404(db: AsyncSession, session_id: str) -> TeachingSession:
    session = await db.get(TeachingSession, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found")
    return session


def _require_matching_session(claims: SessionTokenPayload, session_id: str) -> None:
    """A token minted for session A must never act on session B's routes."""
    if claims.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="session_token_scope_mismatch",
        )


async def _finish(db: AsyncSession, recorded: RecordedEvent) -> SessionStateResponse:
    """Commit the Postgres write, then best-effort broadcast (see event_log.py docstring
    for why this order is the one that keeps a Redis subscriber from ever seeing a
    write that later failed to commit)."""
    await db.commit()
    if not recorded.duplicate:
        await live_sync.set_hot_state(recorded.read_model)
        await live_sync.publish_event(recorded.event)
    return _to_state_response(recorded.read_model)


@router.post("/{session_id}/slide", response_model=SessionStateResponse)
async def advance_slide(
    session_id: str,
    body: AdvanceSlideRequest,
    claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> SessionStateResponse:
    """Teacher advances the projected slide -- emits `slide_changed`."""
    _require_matching_session(claims, session_id)
    await _load_session_or_404(db, session_id)
    recorded = await record_event(
        db,
        session_id=session_id,
        event_type=SessionEventType.SLIDE_CHANGED,
        actor_role=claims.role,
        payload=body.model_dump(),
    )
    return await _finish(db, recorded)


@router.post("/{session_id}/branch", response_model=SessionStateResponse)
async def select_branch(
    session_id: str,
    body: SelectBranchRequest,
    claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> SessionStateResponse:
    """Teacher selects a branch path -- emits `branch_selected`."""
    _require_matching_session(claims, session_id)
    await _load_session_or_404(db, session_id)
    recorded = await record_event(
        db,
        session_id=session_id,
        event_type=SessionEventType.BRANCH_SELECTED,
        actor_role=claims.role,
        payload=body.model_dump(),
    )
    return await _finish(db, recorded)


@router.get("/{session_id}/branches", response_model=ListPrecomputedBranchesResponse)
async def get_precomputed_branches(
    session_id: str,
    slide_id: str,
    claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> ListPrecomputedBranchesResponse:
    """The zero-latency default the cockpit lists FIRST (TSP-06 amendment #2)
    -- no LLM call on this path. Controller-only: only the teacher acts on
    branch options, same gating `/branch` itself uses."""
    _require_matching_session(claims, session_id)
    session = await _load_session_or_404(db, session_id)
    branches = await list_precomputed_branches(db, deck_id=session.deck_id, slide_id=slide_id)
    return ListPrecomputedBranchesResponse(
        branches=[
            PrecomputedBranchResponse(
                branch_id=branch.branch_id,
                slide_id=branch.slide_id,
                interaction_id=branch.interaction_id,
                branch_type=BranchContentType(branch.branch_type),
                label=branch.label,
            )
            for branch in branches
        ],
    )


@router.post("/{session_id}/branch-suggestions", response_model=BranchSuggestionResponse)
async def suggest_branch_content(
    session_id: str,
    body: BranchSuggestionRequest,
    claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> BranchSuggestionResponse:
    """On-the-fly AI branch suggestion (TSP-06 amendment #1): the FALLBACK for
    when no precomputed branch fits, reusing SDE-08's exact
    `resolve_rewrite_instruction` + `generate_slide_deck_block_rewrite`
    pipeline -- not a separate live-generation system.

    Returns a teacher-only draft straight in this response body: never
    persisted, never logged as a session event, never handed to the module
    that broadcasts to subscribers -- structurally unreachable from any
    student/display SSE connection (see `branches.py` module docstring).
    Only `/branch-suggestions/apply`, gated behind the teacher's explicit
    "Apply" on the reused confirmation modal, can turn this into
    student-visible content.
    """
    _require_matching_session(claims, session_id)
    await _load_session_or_404(db, session_id)
    try:
        instruction = resolve_rewrite_instruction(preset=body.preset, freeform=body.instruction)
    except BlockRewriteInstructionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc),
        ) from exc

    rewritten = await generate_slide_deck_block_rewrite(
        run_id=session_id, current_body=body.current_body, instruction=instruction,
    )
    if rewritten is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="rewrite_unavailable")
    return BranchSuggestionResponse(
        slide_id=body.slide_id, before=body.current_body, after=rewritten,
    )


@router.post("/{session_id}/branch-suggestions/apply", response_model=SessionStateResponse)
async def apply_branch_suggestion(
    session_id: str,
    body: ApplyBranchSuggestionRequest,
    claims: Annotated[SessionTokenPayload, Depends(require_controller)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> SessionStateResponse:
    """Teacher-approved promotion of an AI suggestion (TSP-06 base AC6):
    quality-gates `approved_body` through the SAME gate a precomputed branch
    must pass (`create_precomputed_branch`), then -- only on success --
    records `branch_selected` with `source="ai_generated"`, the FINAL
    approved content, never the raw suggestion this route received.
    """
    _require_matching_session(claims, session_id)
    session = await _load_session_or_404(db, session_id)

    created = await create_precomputed_branch(
        db,
        deck_id=session.deck_id,
        slide_id=body.slide_id,
        branch_type=body.branch_type,
        label=body.label,
        body=body.approved_body,
        created_by=f"controller:{session_id}",
        interaction_id=body.interaction_id,
        source=BranchSource.AI_GENERATED,
    )
    if isinstance(created, BranchRejected):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"reason": created.reason, "codes": [report.code for report in created.reports]},
        )

    recorded = await record_event(
        db,
        session_id=session_id,
        event_type=SessionEventType.BRANCH_SELECTED,
        actor_role=claims.role,
        payload={
            "slide_id": body.slide_id,
            "branch_id": created.branch_id,
            "source": BranchSource.AI_GENERATED.value,
        },
    )
    return await _finish(db, recorded)


@router.post("/{session_id}/responses", response_model=SessionStateResponse)
async def submit_response(
    session_id: str,
    body: SubmitResponseRequest,
    claims: Annotated[SessionTokenPayload, Depends(require_session_role(SessionRole.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
) -> SessionStateResponse:
    """Student submits/updates an interaction response -- emits `aggregate_updated`.

    Base AC6: `Idempotency-Key` is required, not optional. The lock+check
    happens *before* calling `record_response` (which is not itself
    idempotency-aware -- it always increments) so a duplicate/retried
    request never double-counts TSP-05's aggregate; only a genuinely new key
    reaches `record_response` at all.
    """
    _require_matching_session(claims, session_id)
    session = await _load_session_or_404(db, session_id)

    await lock_session_events(db, session_id)
    existing = await find_by_idempotency_key(db, session_id, idempotency_key)
    if existing is not None:
        state = await current_state(db, session_id)
        await db.commit()
        return _to_state_response(state)

    student_pseudonym = _student_pseudonym(claims, session_id)
    result = await record_response(
        db,
        response_id=f"resp-{uuid4()}",
        session_id=session_id,
        interaction_id=body.interaction_id,
        retention_tier=session.retention_tier,
        kind=body.kind,
        payload=body.payload,
        student_pseudonym=student_pseudonym,
        kc_ids=body.kc_ids,
        correct=body.correct,
        interaction_allows_free_text=body.interaction_allows_free_text,
        session_allows_free_text=body.session_allows_free_text,
    )
    if isinstance(result, ResponseRejected):
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=result.reason)

    categories = allowed_data_categories_for_tier(session.retention_tier)
    if SessionDataCategory.EVENTS not in categories:
        # TSP-01 AC4 "none" tier: fully ephemeral -- no significant event is
        # logged or broadcast for a raw student response either.
        await db.commit()
        state = await current_state(db, session_id)
        return _to_state_response(state)

    tallies = await _current_tallies(db, session_id, body.interaction_id)
    recorded = await record_event(
        db,
        session_id=session_id,
        event_type=SessionEventType.AGGREGATE_UPDATED,
        actor_role=claims.role,
        payload={"interaction_id": body.interaction_id, "tallies": tallies},
        idempotency_key=idempotency_key,
    )
    return await _finish(db, recorded)


def _student_pseudonym(claims: SessionTokenPayload, session_id: str) -> str:
    """Best-effort per-student key from what the join-time token already carries.

    ponytail: a fully anonymous join (no alias, no roster entry) mints no
    per-connection identifier today (TSP-02's token has no `sub`/`jti`), so
    every anonymous student in one session collapses onto the same
    `anon:{session_id}` bucket here. Harmless for aggregate/none tiers (no
    per-student breakdown exists there anyway); only matters for
    pseudonymous/identifiable-tier drill-down, which is TSP-05's territory --
    fix by having TSP-02 mint a stable per-connection id if that gap bites.
    """
    return claims.roster_student_id or claims.alias or f"anon:{session_id}"


async def _current_tallies(
    db: AsyncSession, session_id: str, interaction_id: str,
) -> dict[str, int]:
    aggregates = await get_session_aggregates(db, session_id=session_id)
    matching = next((a for a in aggregates if a.interaction_id == interaction_id), None)
    if matching is None:
        return {"attempt_count": 0, "correct_count": 0}
    return {"attempt_count": matching.attempt_count, "correct_count": matching.correct_count}


@router.get("/{session_id}/state", response_model=SessionStateResponse)
async def get_current_state(
    session_id: str,
    claims: Annotated[SessionTokenPayload, Depends(get_session_claims)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
) -> SessionStateResponse:
    """Reconnect flow (base AC4): session ID + role token -> current derived state.

    Redis-hot first; Postgres replay-recovery on a Redis miss/outage. Also
    doubles as the polling-fallback transport for a client that can't hold
    an SSE connection open.
    """
    _require_matching_session(claims, session_id)
    await _load_session_or_404(db, session_id)
    state = await current_state(db, session_id)
    return _to_state_response(state)


@router.get("/{session_id}/stream")
async def stream_session_events(
    session_id: str,
    claims: Annotated[SessionTokenPayload, Depends(get_session_claims_for_stream)],
    db: Annotated[AsyncSession, Depends(get_teaching_pack_session)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    """SSE broadcast (base AC3). Replays missed events via `Last-Event-ID` (base AC5),
    then relays live Redis Pub/Sub events; degrades to polling Postgres if Redis is
    unreachable (base AC7 -- live sync degrades, it never just stops).

    Uses `get_session_claims_for_stream` (query-param fallback), not the plain
    `get_session_claims` every other route here uses -- TSP-04's browser
    `EventSource` consumer can't set an Authorization header on the request
    that opens this connection (see that dependency's docstring)."""
    _require_matching_session(claims, session_id)
    await _load_session_or_404(db, session_id)
    after_sequence = int(last_event_id) if last_event_id else 0
    return StreamingResponse(
        _sse_relay(db, session_id, after_sequence),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _format_sse(event: SessionEvent) -> str:
    data: dict[str, Any] = {
        "sequence": event.sequence,
        "event_type": event.event_type.value,
        "actor_role": event.actor_role.value,
        **event.payload,
    }
    encoded = orjson.dumps(data).decode()
    return f"id: {event.sequence}\nevent: {event.event_type.value}\ndata: {encoded}\n\n"


async def _sse_relay(db: AsyncSession, session_id: str, after_sequence: int):
    last_sequence = after_sequence
    for row in await replay_events(db, session_id, after_sequence=after_sequence):
        last_sequence = max(last_sequence, row.sequence)
        yield _format_sse(row_to_event(row))

    try:
        async for event in live_sync.subscribe(session_id):
            if event.sequence is not None and event.sequence <= last_sequence:
                continue  # already replayed above
            last_sequence = event.sequence or last_sequence
            yield _format_sse(event)
    except (RedisError, OSError):
        # Redis Pub/Sub unreachable -- degrade to polling Postgres directly
        # (base AC3's "polling fallback"), same wait/poll shape as
        # `teaching_pack_stream.py`, without the single-process in-memory bus
        # that pattern uses (the amendment's explicit "don't extend it" call).
        async for chunk in _poll_relay(db, session_id, last_sequence):
            yield chunk


class PacingNudgePreferenceResponse(BaseModel):
    enabled: bool


class SetPacingNudgePreferenceRequest(BaseModel):
    enabled: bool


@router.get("/preferences/pacing-nudge", response_model=PacingNudgePreferenceResponse)
async def get_pacing_nudge_preference(
    request: Request,
    teacher: Annotated[User, Depends(require_teacher)],
) -> PacingNudgePreferenceResponse:
    """TSP-04 amendment #2: the cockpit's pacing nudge is opt-in, never
    default-on -- this is what the cockpit reads before ever comparing
    elapsed time to a slide's `planned_duration_minutes`. Gated by the
    teacher's own account JWT (not a session-role token): this is a
    per-teacher setting, not scoped to one live session.
    """
    preference = read_pacing_nudge_preference(request.app.state.store, teacher.user_id)
    return PacingNudgePreferenceResponse(enabled=bool(preference["enabled"]))


@router.put("/preferences/pacing-nudge", response_model=PacingNudgePreferenceResponse)
async def set_pacing_nudge_preference(
    request: Request,
    body: SetPacingNudgePreferenceRequest,
    teacher: Annotated[User, Depends(require_teacher)],
) -> PacingNudgePreferenceResponse:
    write_pacing_nudge_preference(request.app.state.store, teacher.user_id, enabled=body.enabled)
    return PacingNudgePreferenceResponse(enabled=body.enabled)


async def _poll_relay(db: AsyncSession, session_id: str, last_sequence: int):
    while True:
        rows = await replay_events(db, session_id, after_sequence=last_sequence)
        if not rows:
            await anyio.sleep(_POLL_INTERVAL_SECONDS)
            yield ": heartbeat\n\n"
            continue
        for row in rows:
            last_sequence = max(last_sequence, row.sequence)
            yield _format_sse(row_to_event(row))
