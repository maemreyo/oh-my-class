"""Teacher audit log middleware — records teacher decisions to the audit logger."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext

if TYPE_CHECKING:
    from packages.agents.state import OhMyClassState


audit_logger = logging.getLogger("oh_my_class.audit")


class TeacherAuditLogMiddleware(BaseMiddleware):
    """Logs teacher approval/rejection decisions for audit trail."""

    name: str = "teacher_audit_log"
    order: int = 9

    async def before_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        return state

    async def after_model(
        self,
        state: OhMyClassState,
        context: MiddlewareContext,
    ) -> OhMyClassState:
        if state.get("teacher_decision"):
            audit_logger.info(
                "Teacher decision: run_id=%s teacher_id=%s decision=%s step=%s",
                state.get("run_id"),
                state.get("teacher_id"),
                state.get("teacher_decision"),
                state.get("step"),
            )
        return state
