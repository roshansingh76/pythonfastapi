from fastapi import HTTPException
from sqlalchemy.orm import Session
from src.schemas.users_schema import UserCreate
from src.service.user_service import UserService


async def register_user(db:Session,data:UserCreate):
    user = UserService(db).createUser(data)
    return user
   