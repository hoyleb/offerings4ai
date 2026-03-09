from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db import get_session
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
DbSession = Annotated[Session, Depends(get_session)]
TokenDependency = Annotated[str, Depends(oauth2_scheme)]


def get_db():
    yield from get_session()


def get_current_user(token: TokenDependency, db: DbSession) -> User:
    subject = decode_access_token(token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, UUID(subject))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
