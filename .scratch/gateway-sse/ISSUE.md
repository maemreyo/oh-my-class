---
title: "Gateway Lifespan + Runs Router + SSE"
status: ready-for-agent
labels: []
created: 2026-06-23
github: 11
---

## What to build

Implement the FastAPI gateway lifespan in `services/gateway/main.py` and the runs router in `services/gateway/routers/runs.py`. Both files exist with stubs.

## Current State

```python
# services/gateway/main.py (lines 16-22)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: Initialize PostgresSaver/MemorySaver based on ENV
    # TODO: Initialize LiteLLM client
    yield
    # TODO: Cleanup connections

# services/gateway/routers/runs.py — STUB (not read yet, needs implementation)
# services/gateway/main.py lines 25-50 — app setup COMPLETE
```

## Implementation Spec

### 1. Replace `lifespan()` stub (lines 16-22)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — initialize checkpointer, LLM clients."""
    import os
    from packages.agents.checkpointer import get_checkpointer
    
    # 1. Initialize checkpointer based on environment
    environment = os.getenv("OMC_ENVIRONMENT", "development")
    app.state.checkpointer = get_checkpointer(environment)
    
    # 2. Initialize LiteLLM client (if needed)
    # LiteLLM is used via litellm.acompletion() directly, no client needed
    
    # 3. Initialize in-memory run storage (for MVP)
    app.state.runs: dict[str, dict] = {}
    
    yield
    
    # 4. Cleanup connections
    app.state.runs.clear()
```

### 2. Create `services/gateway/routers/runs.py` (replace stub)

```python
"""Runs router — run lifecycle management endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..auth.dependencies import require_teacher

router = APIRouter()


class RunRequest(BaseModel):
    """Request body for creating a new run."""
    raw_request: str
    class_info: dict[str, Any]
    teacher_id: str


class RunResponse(BaseModel):
    """Response from run endpoints."""
    run_id: str
    status: str
    state: dict[str, Any] | None = None


@router.post("", response_model=RunResponse)
async def create_run(
    request: RunRequest,
    user: dict = Depends(require_teacher),
) -> RunResponse:
    """Create a new run and invoke graph asynchronously.
    
    Args:
        request: Run creation request.
        user: Authenticated teacher user.
    
    Returns:
        RunResponse with run_id and status.
    """
    import asyncio
    from packages.agents.graph import build_oh_my_class_graph
    from packages.agents.state import OhMyClassState
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    # Initialize state
    initial_state: OhMyClassState = {
        "raw_request": request.raw_request,
        "teacher_id": request.teacher_id,
        "class_info": request.class_info,
        "run_id": run_id,
        "blueprint_approved": False,
        "quality_passed": False,
        "teacher_approved": False,
        "revision_count": 0,
        "artifact_types": [],
        "theme": "default",
        "artifacts": [],
        "export_formats": [],
        "exported_files": [],
        "current_step": 1,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "research_policy": "standard",
    }
    
    # Store run in memory (MVP)
    # In production, this would use the checkpointer
    app_state = None  # Would be request.app.state in real FastAPI
    
    # Build and invoke graph asynchronously
    async def _invoke_graph():
        try:
            graph = build_oh_my_class_graph(environment="development")
            # In real implementation, would use checkpointer and stream events
            # For now, just store the initial state
            pass
        except Exception as e:
            print(f"Graph invocation failed: {e}")
    
    # Fire and forget (non-blocking)
    asyncio.create_task(_invoke_graph())
    
    return RunResponse(
        run_id=run_id,
        status="created",
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    user: dict = Depends(require_teacher),
) -> RunResponse:
    """Load run state from checkpointer.
    
    Args:
        run_id: The run ID to load.
        user: Authenticated teacher user.
    
    Returns:
        RunResponse with state.
    """
    # TODO: Load from checkpointer
    # For MVP, return placeholder
    return RunResponse(
        run_id=run_id,
        status="running",
        state={"current_step": 1},
    )


@router.get("/{run_id}/status")
async def get_run_status(
    run_id: str,
    user: dict = Depends(require_teacher),
) -> StreamingResponse:
    """SSE stream of graph events.
    
    Args:
        run_id: The run ID to stream.
        user: Authenticated teacher user.
    
    Returns:
        StreamingResponse with SSE events.
    """
    async def event_generator():
        import asyncio
        import json
        
        # Send initial event
        yield f"event: step_start\ndata: {json.dumps({'step': 1, 'run_id': run_id})}\n\n"
        
        # In real implementation, would stream LangGraph events
        # For now, simulate a few events
        for step in range(1, 4):
            await asyncio.sleep(1)
            yield f"event: step_end\ndata: {json.dumps({'step': step, 'status': 'completed'})}\n\n"
        
        yield f"event: complete\ndata: {json.dumps({'run_id': run_id, 'status': 'done'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

## Acceptance criteria

- [ ] `lifespan()` initializes checkpointer on startup
- [ ] `lifespan()` stores checkpointer in `app.state`
- [ ] `lifespan()` clears runs on shutdown
- [ ] `POST /run` creates run and returns `run_id`
- [ ] `POST /run` returns status "created"
- [ ] `POST /run` requires JWT authentication
- [ ] `GET /run/{run_id}` returns run state
- [ ] `GET /run/{run_id}` requires JWT authentication
- [ ] `GET /run/{run_id}/status` returns StreamingResponse
- [ ] `GET /run/{run_id}/status` has correct SSE headers
- [ ] SSE events include step_start, step_end, complete
- [ ] Unit test: lifespan initializes checkpointer
- [ ] Unit test: create_run returns run_id
- [ ] Unit test: get_run returns state
- [ ] Integration test: SSE stream sends events

## Test suite

Create `services/gateway/routers/tests/test_runs.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from services.gateway.main import app


client = TestClient(app)


class TestRunsRouter:
    def test_create_run_requires_auth(self):
        response = client.post("/run", json={
            "raw_request": "Teach photosynthesis",
            "class_info": {"grade": 5},
            "teacher_id": "t-001",
        })
        assert response.status_code == 401
    
    def test_get_run_requires_auth(self):
        response = client.get("/run/test-run-123")
        assert response.status_code == 401
    
    def test_get_run_status_returns_sse(self):
        # Mock auth
        with patch("services.gateway.auth.dependencies.require_teacher"):
            response = client.get(
                "/run/test-run-123/status",
                headers={"Authorization": "Bearer test-token"},
            )
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
```

## File paths

| File | Action |
|------|--------|
| `services/gateway/main.py` | MODIFY: Replace lifespan stub (lines 16-22) |
| `services/gateway/routers/runs.py` | MODIFY: Replace stub with full implementation |
| `services/gateway/routers/tests/test_runs.py` | CREATE: Full test suite |

## Dependencies

- `packages/agents/graph.py` — build_oh_my_class_graph (created in Issue #4)
- `packages/agents/checkpointer.py` — get_checkpointer (created in Issue #4)
- `fastapi` — StreamingResponse (already installed)
- `uuid` — Run ID generation (stdlib)

## Edge cases to handle

1. Unknown run_id → 404 or empty state
2. Graph invocation fails → log error, don't crash
3. SSE client disconnects → stop streaming
4. Multiple concurrent runs → each gets unique run_id
5. Missing checkpointer → use MemorySaver as fallback
