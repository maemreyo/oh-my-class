"""Run management — create, query, and stream pipeline runs."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated, Any

import orjson
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from ..auth.dependencies import require_teacher
from ..auth.models import Role, User
from ..exceptions import AuthorizationError, NotFoundError, PipelineError

router = APIRouter()

# ── In-memory event store ──────────────────────────────────────────────────

_TERMINAL_EVENTS = {"step_completed", "run_failed", "interrupt"}
_event_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
_event_subscribers: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = defaultdict(list)


def _has_terminal_event(run_id: str) -> bool:
    return any(e["event_type"] in _TERMINAL_EVENTS for e in _event_store.get(run_id, []))


def emit_run_event(run_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Append an event to the run's event log and notify subscribers."""
    event = {
        "event_type": event_type,
        "run_id": run_id,
        "timestamp": datetime.now(UTC).isoformat(),
        **data,
    }
    _event_store[run_id].append(event)

    for queue in _event_subscribers[run_id]:
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(event)


def get_run_events(run_id: str) -> list[dict[str, Any]]:
    """Get all events for a run."""
    return list(_event_store.get(run_id, []))


def _format_sse(event: dict[str, Any]) -> str:
    event_type = event.get("event_type", "message")
    payload = {k: v for k, v in event.items() if k != "event_type"}
    data = orjson.dumps(payload).decode()
    return f"event: {event_type}\ndata: {data}\n\n"


class RunRequest(BaseModel):
    """Request body for creating a new run."""

    raw_request: str
    class_info: dict[str, Any]
    teacher_id: str


class RunResponse(BaseModel):
    """Response from run endpoints."""

    run_id: str
    status: str
    topic: str | None = None
    current_step: int | None = None
    artifact_types: list[str] | None = None
    state: dict[str, Any] | None = None


# ── State factory ────────────────────────────────────────────────────────────


def build_initial_state(request: RunRequest, run_id: str) -> dict[str, Any]:
    """Create the initial OhMyClassState dict from a RunRequest."""
    return {
        "raw_request": request.raw_request,
        "teacher_id": request.teacher_id,
        "class_info": request.class_info,
        "run_id": run_id,
        "blueprint_approved": False,
        "research_policy": "standard",
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "export_formats": ["html"],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }


# ── Read model ──────────────────────────────────────────────────────────────


def _build_quality_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Extract quality gate data from state into a focused summary dict.

    Aggregates schema validation, content review, judge scoring, and
    healing strategy fields into a single ``quality`` sub-dict so the
    frontend can render quality status without scanning the full state.
    """
    quality: dict[str, Any] = {}
    if state.get("quality_scores"):
        quality["scores"] = state["quality_scores"]
    if state.get("quality_passed"):
        quality["passed"] = state["quality_passed"]
    if state.get("judge_score") is not None:
        quality["judge_score"] = state["judge_score"]
    if state.get("schema_valid") is not None:
        quality["schema_valid"] = state["schema_valid"]
    if state.get("content_review_passed") is not None:
        quality["content_review_passed"] = state["content_review_passed"]
    if state.get("healing_strategy"):
        quality["healing_strategy"] = state["healing_strategy"]
    if state.get("fail_count", 0) > 0:
        quality["fail_count"] = state["fail_count"]
    if state.get("fail_context"):
        quality["fail_context"] = state["fail_context"]
    return quality


def _to_run_response(run_data: dict[str, Any]) -> RunResponse:
    """Map internal run store data to the API RunResponse schema.

    Extracts summary fields from the state dict so the frontend can access
    run.topic, run.current_step, run.artifact_types directly, while keeping
    the full state available as an opaque blob.  Includes a ``quality``
    sub-dict in state when quality gate data is present.
    """
    state = run_data.get("state", {})

    quality = _build_quality_summary(state)

    enriched_state: dict[str, Any] = dict(state) if state else {}
    if quality:
        enriched_state["quality"] = quality

    return RunResponse(
        run_id=run_data["run_id"],
        status=run_data["status"],
        topic=state.get("lesson_plan", {}).get("topic") if state.get("lesson_plan") else None,
        current_step=state.get("current_step"),
        artifact_types=state.get("artifact_types") or None,
        state=enriched_state or None,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_owner(run_data: dict[str, Any], user: User) -> None:
    """Raise AuthorizationError if user is not the run owner or an admin."""
    if user.role == Role.ADMIN:
        return
    if run_data.get("teacher_id") != user.user_id:
        raise AuthorizationError(
            message="You do not have access to this run",
        )


def _derive_status(state: dict[str, Any]) -> str:
    """Derive a human-readable pipeline status from the current state.

    Status progression:
        running → awaiting_approval → generating → reviewing
        → awaiting_content_approval → exporting → completed

    The ``gate_payload.gate`` field is the most reliable indicator of which
    gate the run is currently blocked on.
    """
    if state.get("error"):
        return "failed"
    if state.get("export_ready") and state.get("exported_files"):
        return "completed"
    if state.get("teacher_approved") and not state.get("exported_files"):
        return "export_ready"
    if state.get("teacher_approved"):
        return "exporting"
    gate = (state.get("gate_payload") or {}).get("gate")
    if gate == "content_approval":
        return "awaiting_content_approval"
    if gate == "blueprint_approval":
        return "awaiting_approval"
    if state.get("blueprint_approved"):
        if state.get("judge_score") is not None:
            return "reviewing"
        if state.get("artifacts"):
            return "generating"
        return "generating"
    if state.get("lesson_plan"):
        return "awaiting_approval"
    return "running"


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("", response_model=list[RunResponse])  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_runs(
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> list[RunResponse]:
    """GET /run — List runs for the current teacher/admin."""
    runs_store = http_request.app.state.runs
    user_id = current_user.user_id
    is_admin = current_user.role == Role.ADMIN

    result: list[RunResponse] = []
    for run_data in runs_store.values():
        # Teachers see only their own runs; admins see all
        if is_admin or run_data.get("teacher_id") == user_id:
            result.append(_to_run_response(run_data))

    return result


@router.post("", response_model=RunResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def create_run(
    http_request: Request,
    run_request: RunRequest,
    current_user: Annotated[User, Depends(require_teacher)],
) -> RunResponse:
    """POST /run — Start a new teaching pack generation run.

    Creates an OhMyClassState, invokes the compiled LangGraph graph,
    persists the run, and returns a structured RunResponse.
    Teacher ID is always derived from the authenticated user —
    request.body teacher_id is ignored.
    """
    run_id = str(uuid.uuid4())
    request_id = getattr(http_request.state, "request_id", None)

    graph = http_request.app.state.graph
    initial_state = build_initial_state(run_request, run_id)
    initial_state["teacher_id"] = current_user.user_id

    emit_run_event(run_id, "run_created", {
        "status": "running",
        "current_step": 1,
        "raw_request": run_request.raw_request[:100],
    })

    try:
        state = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": run_id}},
        )
    except Exception as exc:
        emit_run_event(run_id, "run_failed", {"error": str(exc)[:200]})
        raise PipelineError(
            message=f"Graph invocation failed: {exc}",
            run_id=run_id,
            request_id=request_id,
        ) from exc

    status = _derive_status(state)

    emit_run_event(run_id, "step_completed", {
        "status": status,
        "current_step": state.get("current_step", 1),
    })

    if state.get("gate_payload"):
        emit_run_event(run_id, "interrupt", {
            "gate": state["gate_payload"].get("gate", "unknown"),
            "current_step": state.get("current_step"),
            **{k: v for k, v in state["gate_payload"].items() if k != "gate"},
        })

    http_request.app.state.runs[run_id] = {
        "run_id": run_id,
        "status": status,
        "state": state,
        "teacher_id": current_user.user_id,
        "created_at": datetime.now(UTC).isoformat(),
    }

    return _to_run_response(http_request.app.state.runs[run_id])


@router.get("/{run_id}", response_model=RunResponse)  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_run(
    run_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> RunResponse:
    """GET /run/{id} — Get run state and current step."""
    run_data = http_request.app.state.runs.get(run_id)
    if run_data is None:
        raise NotFoundError(
            message=f"Run {run_id} not found",
            request_id=getattr(http_request.state, "request_id", None),
        )

    _require_owner(run_data, current_user)
    return _to_run_response(run_data)


@router.get("/{run_id}/status")  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_run_status(
    run_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> StreamingResponse:
    """GET /run/{id}/status — SSE stream of real pipeline progress."""
    run_data = http_request.app.state.runs.get(run_id)
    if run_data is None:
        raise NotFoundError(
            message=f"Run {run_id} not found",
            request_id=getattr(http_request.state, "request_id", None),
        )

    _require_owner(run_data, current_user)

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    _event_subscribers[run_id].append(queue)

    async def event_generator():
        try:
            for event in get_run_events(run_id):
                yield _format_sse(event)

            if _has_terminal_event(run_id):
                return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    if event is None:
                        break
                    yield _format_sse(event)
                except TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            _event_subscribers[run_id].remove(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/exports")  # pyright: ignore[reportUntypedFunctionDecorator]
async def list_exports(
    run_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> list[dict[str, Any]]:
    """GET /run/{id}/exports — List exported files for a run."""
    run_data = http_request.app.state.runs.get(run_id)
    if run_data is None:
        raise NotFoundError(
            message=f"Run {run_id} not found",
            request_id=getattr(http_request.state, "request_id", None),
        )

    _require_owner(run_data, current_user)

    state = run_data.get("state", {})
    exported = state.get("exported_files", [])

    return [
        {
            "artifact_id": f.get("artifact_id"),
            "format": f.get("format"),
            "title": f.get("title"),
            "artifact_type": f.get("artifact_type"),
        }
        for f in exported
    ]


@router.get("/{run_id}/exports/{artifact_id}")  # pyright: ignore[reportUntypedFunctionDecorator]
async def download_export(
    run_id: str,
    artifact_id: str,
    http_request: Request,
    current_user: Annotated[User, Depends(require_teacher)],
) -> Response:
    """GET /run/{id}/exports/{artifact_id} — Download exported file."""
    run_data = http_request.app.state.runs.get(run_id)
    if run_data is None:
        raise NotFoundError(
            message=f"Run {run_id} not found",
            request_id=getattr(http_request.state, "request_id", None),
        )

    _require_owner(run_data, current_user)

    state = run_data.get("state", {})
    exported = state.get("exported_files", [])

    for f in exported:
        if f.get("artifact_id") == artifact_id:
            content = f.get("content", "")
            format_type = f.get("format", "html")
            if format_type == "html":
                return HTMLResponse(content=content)
            return Response(content=content, media_type="application/octet-stream")

    raise NotFoundError(
        message=f"Export {artifact_id} not found in run {run_id}",
        request_id=getattr(http_request.state, "request_id", None),
    )
