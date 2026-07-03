"""Teacher audit log middleware — records teacher decisions to the audit logger."""

from __future__ import annotations

import logging
from packages.agents.middleware.base import BaseMiddleware, MiddlewareContext, MiddlewareState


audit_logger = logging.getLogger("oh_my_class.audit")


class TeacherAuditLogMiddleware(BaseMiddleware):
    """Logs teacher approval/rejection decisions for audit trail."""

    name: str = "teacher_audit_log"
    order: int = 8

    async def before_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        return state

    async def after_model(
        self,
        state: MiddlewareState,
        _context: MiddlewareContext,
    ) -> MiddlewareState:
        if state.get("teacher_decision"):
            audit_logger.info(
                "Teacher decision: run_id=%s teacher_id=%s decision=%s step=%s",
                state.get("run_id"),
                state.get("teacher_id"),
                state.get("teacher_decision"),
                state.get("step"),
            )
        return state
