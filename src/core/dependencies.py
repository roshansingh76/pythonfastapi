"""
Reusable FastAPI dependencies.
"""

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.core.security import decode_access_token
from src.models.user_model import User
from src.repository.user_repository import UserRepository
from src.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the Bearer token and return the authenticated User.

    Raises HTTP 401 for any invalid / expired token.
    Raises HTTP 404 if the token's subject no longer exists in the DB.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        logger.warning("Invalid JWT token received")
        raise credentials_exception

    try:
        user = UserRepository(db).get_by_id(int(user_id))
    except NotFoundError:
        raise credentials_exception

    return user
