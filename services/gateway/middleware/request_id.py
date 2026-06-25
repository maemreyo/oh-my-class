"""Request ID middleware — generates and propagates X-Request-ID headers.

Each request gets a stable request-id:
- If the client sent a valid X-Request-ID, it is reused.
- Otherwise, a fresh UUID4 is generated.

The id is stored in ``request.state.request_id``, bound to the logger context
(via :func:`logging_config.bind_context`), and echoed back on the response as
``X-Request-ID`` so teachers / clients can correlate logs.

Order note: this middleware MUST be added BEFORE ``JWTMiddleware`` so that
auth failures still carry a request-id in their response and logs.
"""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

from ..logging_config import bind_context, get_logger

if TYPE_CHECKING:
    from starlette.requests import Request

_HEADER_NAME = "X-Request-ID"

# UUID-shaped: alphanumeric + dashes, length 8-64.
_VALID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")

_logger = get_logger("services.gateway.request_id")


def generate_request_id() -> str:
    """Return a fresh request-id (UUID4 string)."""
    return str(uuid.uuid4())


def _is_valid_request_id(value: str) -> bool:
    """Return True if ``value`` is a plausible request-id (UUID-shaped).

    Loose check: only hex chars + dashes allowed, length 8-64.
    Empty or whitespace-only strings are rejected.
    """
    if not value:
        return False
    return bool(_VALID_RE.match(value))


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns/propagates a request-id for every request."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(_HEADER_NAME)
        if incoming and _is_valid_request_id(incoming):
            request_id = incoming
        else:
            request_id = generate_request_id()

        request.state.request_id = request_id

        # Bind context — include teacher_id if JWT middleware already ran.
        teacher_id = getattr(request.state, "user_id", None)
        bound = bind_context(_logger, request_id=request_id, teacher_id=teacher_id)
        bound.info("request.received path=%s method=%s", request.url.path, request.method)

        response = await call_next(request)
        response.headers[_HEADER_NAME] = request_id
        return response
