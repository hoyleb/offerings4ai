from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db import get_session
from app.models import User

DbSession = Annotated[Session, Depends(get_session)]
settings = get_settings()
session_cookie_scheme = APIKeyCookie(name=settings.session_cookie_name, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
CookieTokenDependency = Annotated[str | None, Depends(session_cookie_scheme)]
BearerDependency = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_db():
    yield from get_session()


def get_current_user(
    cookie_token: CookieTokenDependency,
    bearer: BearerDependency,
    db: DbSession,
) -> User:
    token = bearer.credentials if bearer is not None else cookie_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    subject = decode_access_token(token)
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, UUID(subject))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
