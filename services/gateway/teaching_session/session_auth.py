"""FastAPI dependencies gating session-role-scoped endpoints (TSP-02 base AC5).

Mirrors `services.gateway.auth.dependencies`' `HTTPBearer` + role-check shape,
but decodes a `SessionTokenPayload` (this module's own claim shape) instead
of the account `TokenPayload`. Kept as a wholly separate `HTTPBearer`/
dependency chain on purpose: a session role token is structurally incapable
of satisfying `require_teacher`/`require_admin` (wrong claim shape entirely),
and an account JWT is structurally incapable of satisfying
`require_session_role` (no `session_id`/`room_code` claims) -- so a
student/display/observer token can never reach a teacher-only route gated by
`require_teacher`, and a teacher's own account token can never masquerade as
a session role it was never scoped to.

No live routes are wired to these dependencies yet (TSP-03/04 build the
actual session routes); this module is the reusable enforcement primitive
those slices attach.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.gateway.teaching_session.tokens import (
    SessionRole,
    SessionTokenPayload,
    verify_session_token,
)

session_security = HTTPBearer(auto_error=False)


async def get_session_claims(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(session_security)],
) -> SessionTokenPayload:
    """Extract and verify a session-role JWT from the Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session role token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_session_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_session_claims_for_stream(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(session_security)],
    session_token: Annotated[str | None, Query()] = None,
) -> SessionTokenPayload:
    """Same verification as `get_session_claims`, plus a query-param fallback
    (TSP-04) -- mirrors `auth.dependencies.get_current_user_for_status_stream`'s
    cookie fallback for the same reason: the browser's native `EventSource`
    cannot set an Authorization header, so the live cockpit's `GET /stream`
    consumer (the only caller of this dependency) has no other way to attach
    the session-role token to the request that starts the connection.
    """
    token = credentials.credentials if credentials is not None else session_token
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing session role token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verify_session_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_session_role(*allowed: SessionRole):
    """Dependency factory: only these session roles may reach the route."""

    async def _check(
        claims: Annotated[SessionTokenPayload, Depends(get_session_claims)],
    ) -> SessionTokenPayload:
        if claims.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Session role not permitted for this action",
            )
        return claims

    return _check


# Controller-only actions (branch selection, ending the session, etc.) --
# base AC "student/display/observer tokens cannot access ... controller
# actions".
require_controller = require_session_role(SessionRole.CONTROLLER)
