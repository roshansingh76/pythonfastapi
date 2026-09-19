from fastapi import APIRouter,status,Depends
from fastapi.params import Body
from src.controller import user_controller
from src.schemas.users_schema import UserCreate,UserOut
from src.config.database import get_db
from sqlalchemy.orm import Session
router =APIRouter()


@router.post("/users/register",status_code=status.HTTP_201_CREATED)
async def user_register(data:UserCreate,db:Session=Depends(get_db)):
    user = await user_controller.register_user(db,data)
    return {"status":"ok","message":"User register api","users":user}


@router.post("/users/login")
def user_login():
    return {"status":"ok","message":"User login api"}

@router.post("/users")
def get_users():
    return {"status":"ok","message":"Get Users api"}

@router.delete("/delete/{user_id}")
def delete_users(user_id:int):
    return {"status":"ok","message":"Get Users api"}


@router.put("/update/{user_id}")
def update_users(user_id:int):
    return {"status":"ok","message":"Get Users api"}
