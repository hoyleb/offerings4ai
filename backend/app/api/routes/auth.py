from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import TokenResponse, UserCreate, UserLogin, UserPublic
from app.services.auth import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=UserPublic)
def register(payload: UserCreate, db: DbSession) -> UserPublic:
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: DbSession) -> TokenResponse:
    token = authenticate_user(db, payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return current_user
