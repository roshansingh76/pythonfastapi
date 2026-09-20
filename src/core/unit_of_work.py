"""
Unit of Work (UoW) pattern.

Responsibilities
----------------
- Owns the SQLAlchemy Session for the duration of one business operation.
- Exposes all repositories as attributes so the service layer accesses
  data through a single consistent object.
- commit()   persists every staged change atomically.
- rollback() undoes all staged changes if anything goes wrong.
- Used as a context manager so cleanup is guaranteed even on exceptions.

Usage in a service
------------------
    with UnitOfWork(db) as uow:
        uow.users.add(new_user)
        uow.commit()           # single atomic commit
        uow.db.refresh(new_user)
        return new_user

    # If an exception escapes the `with` block, rollback() is called
    # automatically — no explicit try/except needed in the service.

Why not commit inside the repository?
--------------------------------------
A repository method like create_user() can only see its own INSERT.
The UoW lets you span multiple repositories in one transaction:

    with UnitOfWork(db) as uow:
        uow.users.add(user)
        uow.wallets.add(wallet)   # hypothetical second repo
        uow.commit()              # both committed atomically or neither
"""

import logging

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.exceptions import ConflictError, DatabaseError
from src.repository.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    def __init__(self, db: Session) -> None:
        self.db = db
        # Repositories are initialised once and share the same session.
        self.users = UserRepository(db)

    # ------------------------------------------------------------------
    # Context manager protocol
    # ------------------------------------------------------------------

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            # Any exception that escapes the `with` block → rollback
            self.rollback()
            logger.debug("UoW: rolled back due to %s", exc_type.__name__)
        # Return False so the exception propagates to the caller normally.
        return False

    # ------------------------------------------------------------------
    # Transaction control  (only place commit/rollback should be called)
    # ------------------------------------------------------------------

    def commit(self) -> None:
        """
        Flush and commit the current transaction.

        Translates low-level SQLAlchemy exceptions into domain exceptions
        so the service layer stays completely decoupled from the DB driver.
        """
        try:
            self.db.commit()
            logger.debug("UoW: transaction committed")
        except IntegrityError as exc:
            self.db.rollback()
            logger.warning("UoW: integrity error — %s", exc.orig)
            raise ConflictError("A uniqueness constraint was violated.") from exc
        except SQLAlchemyError as exc:
            self.db.rollback()
            logger.exception("UoW: unexpected SQLAlchemy error")
            raise DatabaseError() from exc

    def rollback(self) -> None:
        """Discard all staged changes for this transaction."""
        try:
            self.db.rollback()
            logger.debug("UoW: transaction rolled back")
        except SQLAlchemyError:
            logger.exception("UoW: error during rollback (connection may be broken)")
