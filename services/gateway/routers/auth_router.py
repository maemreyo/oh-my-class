"""Authentication endpoints — login, token refresh."""

from fastapi import APIRouter, HTTPException, status

from ..auth.jwt_handler import create_access_token
from ..auth.models import LoginRequest, Role, Token, User

router = APIRouter(prefix="/auth", tags=["auth"])

# Placeholder user store — replace with database lookup
DEMO_USERS = {
    "teacher1": User(
        user_id="u-001",
        username="teacher1",
        role=Role.TEACHER,
        email="teacher1@school.edu.vn",
    ),
    "admin": User(
        user_id="u-admin",
        username="admin",
        role=Role.ADMIN,
        email="admin@oh-my-class.dev",
    ),
}


@router.post("/login", response_model=Token)  # pyright: ignore[reportUntypedFunctionDecorator]
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    # TODO: Replace with real password verification (bcrypt)
    user = DEMO_USERS.get(request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return create_access_token(user)


@router.get("/me", response_model=User)  # pyright: ignore[reportUntypedFunctionDecorator]
async def get_me():
    """Get current user info (requires auth header)."""
    # This endpoint is a placeholder — in real use, it requires get_current_user dep
    # The actual auth check happens via middleware or direct dependency
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )
