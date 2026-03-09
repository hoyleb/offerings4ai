from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.schemas import UserCreate


def register_user(db: Session, payload: UserCreate) -> User:
    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        payout_address=payload.payout_address,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> str:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(str(user.id))
