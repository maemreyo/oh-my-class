"""Authentication module — JWT-based auth for the oh-my-class gateway."""

from .dependencies import get_current_user, require_admin, require_teacher
from .jwt_handler import create_access_token, user_from_payload, verify_token
from .models import (
    ADMIN_ROLES,
    TEACHER_ROLES,
    LoginRequest,
    Role,
    Token,
    TokenPayload,
    User,
    WebhookSecret,
)
from .ownership import check_run_owner

__all__ = [
    "ADMIN_ROLES",
    "TEACHER_ROLES",
    "Role",
    "User",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "WebhookSecret",
    "create_access_token",
    "verify_token",
    "user_from_payload",
    "get_current_user",
    "require_teacher",
    "require_admin",
    "check_run_owner",
]
