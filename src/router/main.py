
from fastapi import APIRouter
from src.router import users_router
router =APIRouter()
router.include_router(users_router.router, prefix="/auth", tags=["Auth"])


