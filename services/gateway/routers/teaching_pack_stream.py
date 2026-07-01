"""SSE streaming endpoint for pipeline V2 run status."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import get_current_user_for_status_stream
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.teaching_pack_event_bus import current_run_event_version, wait_for_run_event
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId
from services.gateway.routers.teaching_pack_deps import TEACHING_PACK_SESSION, get_run_with_ownership
from services.gateway.routers.teaching_pack_helpers import format_event_stream

stream_router = APIRouter()


@dataclass(frozen=True, slots=True)
class TeachingPackStreamRequest:
    run_id: RunId
    after_sequence: int
    replay_only: bool


async def stream_visible_run_events(
    store: TeachingPackRunStore,
    request: TeachingPackStreamRequest,
) -> AsyncIterator[str]:
    last_sequence = request.after_sequence
    events = await store.replay_events(request.run_id, after_sequence=request.after_sequence)
    for event in events:
        if event.visibility is TeachingPackEventVisibility.TEACHER:
            last_sequence = max(last_sequence, event.sequence)
            yield format_event_stream(event)
    if request.replay_only:
        return
    while True:
        observed_version = current_run_event_version(request.run_id)
        live_events = await store.replay_events(request.run_id, after_sequence=last_sequence)
        if not live_events:
            woke = await wait_for_run_event(request.run_id, observed_version, timeout_seconds=15.0)
            live_events = await store.replay_events(request.run_id, after_sequence=last_sequence)
            if not woke and not live_events:
                yield ": heartbeat\n\n"
        for event in live_events:
            last_sequence = max(last_sequence, event.sequence)
            if event.visibility is TeachingPackEventVisibility.TEACHER:
                yield format_event_stream(event)


@stream_router.get("/run/{run_id}/status")
@stream_router.get("/runs/{run_id}/status")
async def stream_teaching_pack_status(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user_for_status_stream)],
    session: AsyncSession = TEACHING_PACK_SESSION,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[str | None, Query(alias="last_event_id")] = None,
    replay_only: bool = False,
) -> StreamingResponse:
    await get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    store = TeachingPackRunStore(session)

    requested_last_event_id = last_event_id if last_event_id is not None else last_event_id_query
    after_sequence = int(requested_last_event_id) if requested_last_event_id is not None else 0
    request = TeachingPackStreamRequest(
        run_id=typed_run_id,
        after_sequence=after_sequence,
        replay_only=replay_only,
    )

    return StreamingResponse(
        stream_visible_run_events(store, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
