import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controller import user_controller
from src.core.dependencies import get_current_user
from src.models.user_model import User
from src.schemas.users_schema import TokenOut, UserCreate, UserLogin, UserOut

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Public routes  (no auth required)
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def user_register(data: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    return user_controller.register_user(db, data)


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Authenticate and receive a JWT access token",
)
def user_login(data: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    return user_controller.login_user(db, data)


# ---------------------------------------------------------------------------
# Protected routes  (valid JWT required)
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=list[UserOut],
    summary="List all users — requires authentication",
)
def get_users(
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum records to return"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),   # enforces auth; result unused here
) -> list[UserOut]:
    return user_controller.list_users(db, skip=skip, limit=limit)


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    summary="Retrieve a single user by ID — requires authentication",
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> UserOut:
    return user_controller.get_user(db, user_id)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user by ID — requires authentication",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    user_controller.remove_user(db, user_id)
