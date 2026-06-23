"""Interrupt handler — LangGraph interrupt() for teacher approval gates.

Manages two interrupt points in the pipeline:
1. Blueprint approval (Step 04) — teacher reviews lesson plan
2. Content approval (Step 11) — teacher reviews generated artifacts

INVARIANT-06: Teacher Gate CANNOT be bypassed or self-approved by any agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class GateResponse:
    """Teacher's response to an interrupt gate."""

    action: str  # "approve" | "edit" | "reject"
    feedback: str | None = None
    edits: dict[str, Any] | None = None


@dataclass
class InterruptConfig:
    """Configuration for interrupt gates."""

    timeout_hours: int = 24
    max_revisions: int = 3
    webhook_url: str | None = None  # Telegram/Zalo/email webhook


class InterruptHandler:
    """Manages LangGraph interrupt() calls for teacher approval gates.

    Handles:
    - Creating interrupt points in the graph
    - Sending notifications via webhook
    - Processing teacher responses (approve/edit/reject)
    - Timeout handling → auto-escalate to admin
    - Revision counting → escalate after max_revisions
    """

    def __init__(self, config: InterruptConfig | None = None) -> None:
        self.config = config or InterruptConfig()

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
        # TODO: Implement with langgraph.interrupt()
        # 1. Format state for teacher presentation
        # 2. Send webhook notification
        # 3. Call interrupt() and wait for response
        # 4. Parse teacher response
        # 5. Return GateResponse
        raise NotImplementedError("create_gate() stub — implement with LangGraph interrupt()")

    async def handle_timeout(self, gate_type: str) -> dict[str, Any]:
        """Handle gate timeout — auto-escalate to admin.

        Args:
            gate_type: The gate that timed out.

        Returns:
            Escalation response dict.
        """
        # TODO: Implement timeout handling
        # 1. Log timeout event
        # 2. Send escalation notification to admin
        # 3. Return escalation response
        raise NotImplementedError("handle_timeout() stub — implement admin escalation")
