"""
Controller — thin glue between router and service.
Converts service results / domain exceptions into response schemas.
Domain exceptions propagate up and are caught by the app-level handlers.
"""

from sqlalchemy.orm import Session

from src.core.security import create_access_token
from src.models.user_model import User
from src.schemas.users_schema import TokenOut, UserCreate, UserLogin
from src.service.user_service import UserService


def register_user(db: Session, data: UserCreate) -> User:
    return UserService(db).create_user(data)


def login_user(db: Session, data: UserLogin) -> TokenOut:
    user = UserService(db).authenticate(data.email, data.password)
    token = create_access_token(subject=user.id)
    return TokenOut(access_token=token)


def list_users(db: Session, skip: int = 0, limit: int = 20) -> list[User]:
    return UserService(db).get_all_users(skip=skip, limit=limit)


def get_user(db: Session, user_id: int) -> User:
    return UserService(db).get_user_by_id(user_id)


def remove_user(db: Session, user_id: int) -> None:
    UserService(db).delete_user(user_id)
