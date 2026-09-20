"""
Domain-level exceptions.

These are raised by the service/repository layers and translated to
HTTP responses by exception handlers registered in src/main.py.
No layer below the router should import anything from FastAPI.
"""


class AppError(Exception):
    """Base class for all application errors."""


class NotFoundError(AppError):
    """A requested resource does not exist."""

    def __init__(self, resource: str, identifier: int | str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' not found.")


class ConflictError(AppError):
    """A uniqueness constraint was violated."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class UnauthorizedError(AppError):
    """Authentication failed."""

    def __init__(self, detail: str = "Invalid credentials.") -> None:
        self.detail = detail
        super().__init__(detail)


class DatabaseError(AppError):
    """An unexpected database-level error occurred."""

    def __init__(self, detail: str = "A database error occurred.") -> None:
        self.detail = detail
        super().__init__(detail)
