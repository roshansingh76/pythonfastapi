from sqlalchemy.orm import Session
from src.schemas.users_schema import UserCreate
from src.models.user_model import User
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError,SQLAlchemyError

class UserService:
    def __init__(self,db:Session):
        self.db=db

    def createUser(self,data:UserCreate)->User:
        user = User(
            email=data.email,
            username=data.username,
            password_hash=data.password,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            print(repr(e.orig))  # temporary, shows the real DB error
            raise HTTPException(
                status_code=409,
                detail="Email or username already registered",
            ) from e
        except SQLAlchemyError as e:
            self.db.rollback()
            print(repr(e))  # temporary
            raise
        self.db.refresh(user)
        return user

