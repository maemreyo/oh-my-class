"""SSE streaming endpoint for pipeline V2 run status."""

from __future__ import annotations

from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: TC002

from services.gateway.auth.dependencies import require_teacher
from services.gateway.auth.models import User  # noqa: TC001
from services.gateway.teaching_pack_models import TeachingPackEventVisibility
from services.gateway.teaching_pack_store import TeachingPackRunStore
from services.gateway.teaching_pack_types import RunId
from services.gateway.routers.teaching_pack_deps import TEACHING_PACK_SESSION, _get_run_with_ownership
from services.gateway.routers.teaching_pack_helpers import format_event_stream

stream_router = APIRouter()


@stream_router.get("/run/{run_id}/status")
async def stream_teaching_pack_status(
    run_id: str,
    current_user: Annotated[User, Depends(require_teacher)],
    session: AsyncSession = TEACHING_PACK_SESSION,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    last_event_id_query: Annotated[str | None, Query(alias="last_event_id")] = None,
    replay_only: bool = False,
) -> StreamingResponse:
    await _get_run_with_ownership(run_id, current_user, session)
    typed_run_id = RunId(run_id)
    store = TeachingPackRunStore(session)

    requested_last_event_id = last_event_id if last_event_id is not None else last_event_id_query
    after_sequence = int(requested_last_event_id) if requested_last_event_id is not None else 0
    events = await store.replay_events(typed_run_id, after_sequence=after_sequence)

    async def event_generator():
        last_sequence = after_sequence
        for event in events:
            if event.visibility is TeachingPackEventVisibility.TEACHER:
                last_sequence = max(last_sequence, event.sequence)
                yield format_event_stream(event)
        if replay_only:
            return
        while True:
            await anyio.sleep(1)
            live_events = await store.replay_events(typed_run_id, after_sequence=last_sequence)
            for event in live_events:
                last_sequence = max(last_sequence, event.sequence)
                if event.visibility is TeachingPackEventVisibility.TEACHER:
                    yield format_event_stream(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
