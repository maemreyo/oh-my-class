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

    async def dispatch(self, request: Request, call_next):
        # Skip auth for public paths
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for docs
        if request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

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
