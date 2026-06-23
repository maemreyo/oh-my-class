---
title: "Teacher Gate (Layer 5) + Approvals Router"
status: done
labels: []
created: 2026-06-23
github: 9
---

## What to build

Implement the teacher gate mechanism in `packages/quality/layer5_human/interrupt_handler.py` and the FastAPI approvals router in `services/gateway/routers/approvals.py`. Both files exist with stubs.

## Current State

```python
# packages/quality/layer5_human/interrupt_handler.py (lines 48-68)
async def create_gate(self, gate_type, state) -> dict:
    # TODO: Implement with langgraph.interrupt()
    raise NotImplementedError("create_gate() stub")

# services/gateway/routers/approvals.py — STUB (not read yet, needs implementation)
# packages/quality/layer5_human/interrupt_handler.py lines 70-83 — handle_timeout() stub
```

## Implementation Spec

### 1. Replace `create_gate()` stub (lines 48-68)

```python
async def create_gate(
    self,
    gate_type: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Create an interrupt point for teacher approval.
    
    Args:
        gate_type: One of 'blueprint_approval', 'content_approval'.
        state: Current pipeline state to present to teacher.
    
    Returns:
        Dict with gate details for LangGraph interrupt().
    """
    from langgraph.types import interrupt
    
    # 1. Format state for teacher presentation
    gate_data = {
        "gate": gate_type,
        "actions": ["approve", "edit", "reject"],
        "timestamp": None,  # Will be set by interrupt
    }
    
    # Add gate-specific data
    if gate_type == "blueprint_approval":
        gate_data["lesson_plan"] = state.get("lesson_plan")
    elif gate_type == "content_approval":
        gate_data["artifacts"] = state.get("artifacts")
        gate_data["quality_scores"] = state.get("quality_scores")
    
    # 2. Send webhook notification (optional)
    if self.config.webhook_url:
        await self._send_webhook(gate_type, gate_data)
    
    # 3. Call interrupt() and wait for response
    response = interrupt(gate_data)
    
    # 4. Parse teacher response
    return {
        "action": response.get("action", "reject"),
        "feedback": response.get("feedback"),
        "edits": response.get("edits"),
    }


async def _send_webhook(self, gate_type: str, data: dict[str, Any]) -> None:
    """Send webhook notification for teacher gate."""
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                self.config.webhook_url,
                json={
                    "event": "teacher_gate",
                    "gate_type": gate_type,
                    "data": data,
                },
                timeout=10.0,
            )
    except Exception as e:
        # Log but don't fail
        print(f"Webhook notification failed: {e}")
```

### 2. Replace `handle_timeout()` stub (lines 70-83)

```python
async def handle_timeout(self, gate_type: str) -> dict[str, Any]:
    """Handle gate timeout — auto-escalate to admin.
    
    Args:
        gate_type: The gate that timed out.
    
    Returns:
        Escalation response dict.
    """
    # 1. Log timeout event
    print(f"Gate timeout: {gate_type} after {self.config.timeout_hours} hours")
    
    # 2. Send escalation notification to admin
    if self.config.webhook_url:
        await self._send_webhook(f"{gate_type}_timeout", {"escalated": True})
    
    # 3. Return escalation response
    return {
        "action": "escalate",
        "reason": f"Gate {gate_type} timed out after {self.config.timeout_hours} hours",
        "auto_approved": True,  # Auto-approve on timeout
    }
```

### 3. Create `services/gateway/routers/approvals.py` (replace stub)

```python
"""Approvals router — teacher approval/rejection endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth.dependencies import require_teacher

router = APIRouter()


class ApprovalRequest(BaseModel):
    """Request body for approval/rejection."""
    action: str  # "approve" | "edit" | "reject"
    feedback: str | None = None
    edits: dict[str, Any] | None = None


class ApprovalResponse(BaseModel):
    """Response from approval endpoint."""
    status: str
    message: str
    run_id: str


@router.post("/{run_id}/approve", response_model=ApprovalResponse)
async def approve_run(
    run_id: str,
    request: ApprovalRequest,
    user: dict = Depends(require_teacher),
) -> ApprovalResponse:
    """Approve content and resume graph execution.
    
    Args:
        run_id: The run ID to approve.
        request: Approval request with action and optional feedback.
        user: Authenticated teacher user.
    
    Returns:
        ApprovalResponse with status.
    """
    # TODO: Implement with LangGraph resume
    # 1. Load graph state from checkpointer
    # 2. Resume graph with approval response
    # 3. Return success
    
    return ApprovalResponse(
        status="resumed",
        message=f"Run {run_id} approved and resumed",
        run_id=run_id,
    )


@router.post("/{run_id}/reject", response_model=ApprovalResponse)
async def reject_run(
    run_id: str,
    request: ApprovalRequest,
    user: dict = Depends(require_teacher),
) -> ApprovalResponse:
    """Reject content and resume graph with feedback.
    
    Args:
        run_id: The run ID to reject.
        request: Rejection request with feedback.
        user: Authenticated teacher user.
    
    Returns:
        ApprovalResponse with status.
    """
    if not request.feedback:
        raise HTTPException(
            status_code=400,
            detail="Feedback required for rejection",
        )
    
    # TODO: Implement with LangGraph resume
    # 1. Load graph state from checkpointer
    # 2. Resume graph with rejection response
    # 3. Return success
    
    return ApprovalResponse(
        status="resumed",
        message=f"Run {run_id} rejected and resumed with feedback",
        run_id=run_id,
    )
```

## Acceptance criteria

- [ ] `create_gate()` calls `langgraph.interrupt()` with gate data
- [ ] `create_gate()` returns teacher response with action/feedback/edits
- [ ] `handle_timeout()` returns escalation response
- [ ] `handle_timeout()` sends webhook notification
- [ ] `POST /run/{run_id}/approve` requires JWT authentication
- [ ] `POST /run/{run_id}/approve` returns ApprovalResponse
- [ ] `POST /run/{run_id}/reject` requires feedback
- [ ] `POST /run/{run_id}/reject` returns ApprovalResponse
- [ ] Unit test: create_gate returns response
- [ ] Unit test: handle_timeout returns escalation
- [ ] Unit test: approve endpoint requires auth
- [ ] Unit test: reject endpoint requires feedback

## Test suite

Create `packages/quality/layer5_human/tests/test_interrupt_handler.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from packages.quality.layer5_human.interrupt_handler import (
    InterruptHandler,
    InterruptConfig,
)


class TestInterruptHandler:
    def setup_method(self):
        self.handler = InterruptHandler(InterruptConfig(timeout_hours=24))
    
    @pytest.mark.asyncio
    async def test_create_gate_returns_response(self):
        with patch("langgraph.types.interrupt", return_value={"action": "approve"}):
            state = {"lesson_plan": {"topic": "Test"}}
            result = await self.handler.create_gate("blueprint_approval", state)
            
            assert result["action"] == "approve"
    
    @pytest.mark.asyncio
    async def test_handle_timeout_returns_escalation(self):
        result = await self.handler.handle_timeout("blueprint_approval")
        
        assert result["action"] == "escalate"
        assert result["auto_approved"] is True
```

Create `services/gateway/routers/tests/test_approvals.py`:

```python
import pytest
from fastapi.testclient import TestClient
from services.gateway.main import app


client = TestClient(app)


class TestApprovalsRouter:
    def test_approve_requires_auth(self):
        response = client.post("/run/test-run-123/approve", json={"action": "approve"})
        assert response.status_code == 401  # Unauthorized
    
    def test_reject_requires_feedback(self):
        # Mock auth
        with patch("services.gateway.auth.dependencies.require_teacher"):
            response = client.post(
                "/run/test-run-123/reject",
                json={"action": "reject"},
                headers={"Authorization": "Bearer test-token"},
            )
            assert response.status_code == 400
            assert "feedback" in response.json()["detail"].lower()
```

## File paths

| File | Action |
|------|--------|
| `packages/quality/layer5_human/interrupt_handler.py` | MODIFY: Replace stubs (lines 48-83) |
| `services/gateway/routers/approvals.py` | MODIFY: Replace stub with full implementation |
| `packages/quality/layer5_human/tests/test_interrupt_handler.py` | CREATE: Unit tests |
| `services/gateway/routers/tests/test_approvals.py` | CREATE: API tests |

## Dependencies

- `langgraph` — interrupt() function (already installed)
- `fastapi` — APIRouter, Depends (already installed)
- `services/gateway/auth/dependencies.py` — require_teacher (already exists)
- `httpx` — for webhook calls (may need install)

## Edge cases to handle

1. Webhook URL not set → skip notification (don't crash)
2. Webhook fails → log error, continue
3. Teacher provides no feedback on rejection → 400 error
4. Timeout handler called → auto-approve and escalate
5. Multiple concurrent approvals → last write wins
