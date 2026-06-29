"""FastAPI dependencies for authentication and authorization."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt_handler import user_from_payload, verify_token
from .models import ADMIN_ROLES, TEACHER_ROLES, User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    """Extract and verify JWT from Authorization header."""
    try:
        if credentials is None:
            raise ValueError("Missing or invalid Authorization header")
        payload = verify_token(credentials.credentials)
        return user_from_payload(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user_for_status_stream(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    auth_token: Annotated[str | None, Cookie(alias="auth-token")] = None,
) -> User:
    try:
        token = credentials.credentials if credentials is not None else auth_token
        if token is None:
            raise ValueError("Missing or invalid Authorization header")
        payload = verify_token(token)
        return user_from_payload(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def require_teacher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in TEACHER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin role required",
        )
    return current_user


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user
