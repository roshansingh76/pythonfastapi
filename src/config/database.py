"""
Database engine, session factory, and FastAPI dependency.

Lifecycle summary
-----------------
Startup  : create_engine() is called once at import time (module-level singleton).
           The pool is NOT yet populated — connections are opened lazily on first use.
Request  : get_db() opens one Session, yields it to the route handler.
           On success  → commit is done by the service/UoW layer.
           On exception → explicit rollback here ensures the connection is
                          returned to the pool in a clean state.
           Always      → session.close() returns the underlying connection to
                         the pool (it is NOT closed at the TCP level).
Shutdown : engine.dispose() closes every pooled TCP connection gracefully.
           Called from the FastAPI lifespan context in src/main.py.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine  (one per process)
# ---------------------------------------------------------------------------

engine: Engine = create_engine(
    settings.database_url,
    # --- pool behaviour ---
    pool_pre_ping=settings.db_pool_pre_ping,   # cheap SELECT 1 to detect stale connections
    pool_size=settings.db_pool_size,           # persistent connections kept alive
    max_overflow=settings.db_max_overflow,     # burst connections (closed after use)
    pool_timeout=settings.db_pool_timeout,     # seconds to wait for a free slot
    pool_recycle=settings.db_pool_recycle,     # recycle connections older than N seconds
    # --- visibility ---
    echo=settings.debug,                       # log every SQL statement in debug mode
)


# ---------------------------------------------------------------------------
# Pool event hooks — observability & safety
# ---------------------------------------------------------------------------

@event.listens_for(engine, "connect")
def _on_connect(dbapi_conn, connection_record) -> None:  # noqa: ANN001
    """Fired when a brand-new TCP connection is established."""
    logger.debug("DB pool: new connection opened (id=%d)", id(dbapi_conn))


@event.listens_for(engine, "checkout")
def _on_checkout(dbapi_conn, connection_record, connection_proxy) -> None:  # noqa: ANN001
    """Fired every time a connection is checked out of the pool for a request."""
    logger.debug("DB pool: connection checked out (id=%d)", id(dbapi_conn))


@event.listens_for(engine, "checkin")
def _on_checkin(dbapi_conn, connection_record) -> None:  # noqa: ANN001
    """Fired every time a connection is returned to the pool after a request."""
    logger.debug("DB pool: connection checked in  (id=%d)", id(dbapi_conn))


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # we manage transactions explicitly
    autoflush=False,    # flush only on explicit flush() or commit()
    expire_on_commit=False,  # ORM objects remain usable after commit
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Yield one SQLAlchemy Session per HTTP request.

    Transaction contract
    --------------------
    - commit()   must be called by the service/UnitOfWork layer on success.
    - rollback() is called HERE if the route raises any exception, so the
      connection is always returned to the pool in a pristine state.
    - close()    returns the connection to the pool (not the TCP teardown).
    """
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        logger.exception("SQLAlchemy error — rolling back session")
        db.rollback()
        raise
    except Exception:
        # Non-DB exceptions (validation errors, domain errors, etc.)
        # still need a rollback so any implicit flushes are undone.
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def dispose_engine() -> None:
    """
    Close all pooled connections gracefully.
    Call this from the application shutdown hook so the DB server does not
    accumulate idle connections after a rolling restart.
    """
    engine.dispose()
    logger.info("DB engine disposed — all pool connections closed.")


def check_db_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("DB health check failed", exc_info=True)
        return False
