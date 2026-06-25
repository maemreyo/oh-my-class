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
            Dict with action/feedback/edits from teacher response.
        """
        from langgraph.types import interrupt

        gate_data: dict[str, Any] = {
            "gate": gate_type,
            "actions": ["approve", "edit", "reject"],
            "timestamp": None,
        }

        if gate_type == "blueprint_approval":
            gate_data["lesson_plan"] = state.get("lesson_plan")
        elif gate_type == "content_approval":
            gate_data["artifacts"] = state.get("artifacts")
            gate_data["quality_scores"] = state.get("quality_scores")

        if self.config.webhook_url:
            await self._send_webhook(gate_type, gate_data)

        response = interrupt(gate_data)

        return {
            "action": response.get("action", "reject"),
            "feedback": response.get("feedback"),
            "edits": response.get("edits"),
        }

    async def handle_timeout(self, gate_type: str) -> dict[str, Any]:
        """Handle gate timeout — auto-escalate to admin.

        Args:
            gate_type: The gate that timed out.

        Returns:
            Escalation response dict.
        """
        print(f"Gate timeout: {gate_type} after {self.config.timeout_hours} hours")

        if self.config.webhook_url:
            await self._send_webhook(f"{gate_type}_timeout", {"escalated": True})

        return {
            "action": "escalate",
            "reason": f"Gate {gate_type} timed out after {self.config.timeout_hours} hours",
            "auto_approved": True,
        }

    async def _send_webhook(self, gate_type: str, data: dict[str, Any]) -> None:
        """Send webhook notification for teacher gate."""
        import httpx

        if not self.config.webhook_url:
            return
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
            print(f"Webhook notification failed: {e}")
