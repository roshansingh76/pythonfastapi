"""
User repository — pure data access, zero transaction control.

Rules
-----
- Only stages changes: db.add(), db.delete(), db.query().
- Never calls commit(), rollback(), or close().
- Transaction boundaries are owned exclusively by the UnitOfWork
  (src/core/unit_of_work.py).
- Raises domain exceptions so the service layer stays HTTP-agnostic.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.models.user_model import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Read — never mutate, never flush
    # ------------------------------------------------------------------

    def get_by_id(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise NotFoundError("User", user_id)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all(self, skip: int = 0, limit: int = 20) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count(self) -> int:
        """Efficient row count using SELECT COUNT(*) — no full table load."""
        stmt = select(func.count()).select_from(User)
        return self.db.execute(stmt).scalar_one()

    def exists_by_email(self, email: str) -> bool:
        stmt = select(User.id).where(User.email == email)
        return self.db.execute(stmt).first() is not None

    # ------------------------------------------------------------------
    # Write — stage only, no commit/rollback here
    # ------------------------------------------------------------------

    def add(self, user: User) -> None:
        """Stage a new user for insertion. Caller must commit via UoW."""
        self.db.add(user)
        logger.debug("Staged ADD for user email=%s", user.email)

    def remove(self, user: User) -> None:
        """Stage a user for deletion. Caller must commit via UoW."""
        self.db.delete(user)
        logger.debug("Staged DELETE for user id=%d", user.id)
