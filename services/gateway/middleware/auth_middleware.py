"""Optional JWT middleware — validates tokens on protected routes."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from ..auth.jwt_handler import verify_token


class JWTMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT on protected paths.

    Public paths (no auth required):
    - /health
    - /auth/login
    - /docs, /openapi.json

    All other paths require valid JWT.
    """

    PUBLIC_PATHS = {"/health", "/auth/login", "/docs", "/openapi.json", "/redoc"}
    # Webhooks verify an HMAC signature themselves; teaching-session live-sync
    # routes verify a session-role token themselves (`teaching_session.
    # session_auth`, a completely different JWT claim shape/secret usage than
    # this middleware's account-JWT `verify_token` -- see session_auth.py's
    # docstring). Both are "public" from this middleware's point of view
    # because neither carries an account JWT at all (TSP-03).
    PUBLIC_PREFIXES = ("/webhook/", "/teaching-sessions/")

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for docs
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return await call_next(request)

        # Webhooks are public — they use their own signature verification (HMAC)
        if any(request.url.path.startswith(p) for p in self.PUBLIC_PREFIXES):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            cookie_token = request.cookies.get("auth-token", "")
            if not cookie_token:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid Authorization header"},
                )
            if not _allows_cookie_auth(request.url.path):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Missing or invalid Authorization header"},
                )
            auth_header = f"Bearer {cookie_token}"

        token = auth_header[7:]  # Remove "Bearer " prefix
        try:
            payload = verify_token(token)
            # Add user info to request state for downstream use
            request.state.user_id = payload.sub
            request.state.user_role = payload.role
        except ValueError as e:
            return JSONResponse(
                status_code=401,
                content={"detail": str(e)},
            )

        return await call_next(request)


def _allows_cookie_auth(path: str) -> bool:
    parts = path.strip("/").split("/")
    return (
        len(parts) == 4
        and parts[0] == "teaching-packs"
        and parts[1] in {"run", "runs"}
        and parts[3] == "status"
    )
