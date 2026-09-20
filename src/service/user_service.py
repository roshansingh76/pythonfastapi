"""
User service — orchestrates business rules.

Rules
-----
- Depends on UnitOfWork, not on the repository or Session directly.
- Never calls commit() or rollback() manually; delegates to UoW.
- Never raises HTTPException; raises domain exceptions only.
- All password logic (hashing, verification) lives here.
"""

import logging

from sqlalchemy.orm import Session

from src.core.exceptions import UnauthorizedError
from src.core.security import hash_password, verify_password
from src.core.unit_of_work import UnitOfWork
from src.models.user_model import User
from src.schemas.users_schema import UserCreate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_user(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            username=data.username,
            password_hash=hash_password(data.password),
        )
        with UnitOfWork(self._db) as uow:
            uow.users.add(user)
            uow.commit()
            self._db.refresh(user)   # load DB-generated fields (id, created_at…)

        logger.info("User registered: id=%d email=%s", user.id, user.email)
        return user

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_user_by_id(self, user_id: int) -> User:
        # Read-only — no UoW needed, but we still go through the repo
        # so all SQL stays in one place.
        with UnitOfWork(self._db) as uow:
            return uow.users.get_by_id(user_id)

    def get_all_users(self, skip: int = 0, limit: int = 20) -> list[User]:
        with UnitOfWork(self._db) as uow:
            return uow.users.get_all(skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def authenticate(self, email: str, password: str) -> User:
        """
        Validate credentials.
        Always runs the bcrypt comparison even when the email is unknown
        to prevent timing-based user-enumeration attacks.
        """
        with UnitOfWork(self._db) as uow:
            user = uow.users.get_by_email(email)

        # Constant-time path: always call verify_password regardless of whether
        # the user exists. Using a real pre-computed bcrypt hash avoids a
        # ValueError that passlib raises against a malformed/short hash string.
        _DUMMY_HASH = "$2b$12$OpbQU0sU7.oMhkBMHqpNIuNxSzLbTV58bzpwcYgL0MrUTcur/5X46"
        password_ok = verify_password(
            password,
            user.password_hash if user else _DUMMY_HASH,
        )
        if not user or not password_ok:
            raise UnauthorizedError()

        return user

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_user(self, user_id: int) -> None:
        with UnitOfWork(self._db) as uow:
            user = uow.users.get_by_id(user_id)  # raises NotFoundError if missing
            uow.users.remove(user)
            uow.commit()

        logger.info("User deleted: id=%d", user_id)
