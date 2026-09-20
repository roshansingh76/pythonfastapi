import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config.database import check_db_connection, dispose_engine
from src.config.settings import settings
from src.core.exceptions import (
    ConflictError,
    DatabaseError,
    NotFoundError,
    UnauthorizedError,
)
from src.core.logging import configure_logging
from src.router.main import router

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(debug=settings.debug)
    logger.info("Starting %s v%s (debug=%s)", settings.title, settings.version, settings.debug)
    yield
    # ---- shutdown ----
    dispose_engine()   # close all pooled DB connections cleanly
    logger.info("Shutting down %s", settings.title)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.title,
        description=settings.description,
        version=settings.version,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Global exception handlers
    # ------------------------------------------------------------------

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.detail},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(DatabaseError)
    async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        logger.exception("Database error: %s", exc.detail)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred."},
        )

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    app.include_router(router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    def health_check() -> dict:
        db_ok = check_db_connection()
        return {
            "status": "ok" if db_ok else "degraded",
            "version": settings.version,
            "database": "up" if db_ok else "down",
        }

    return app
