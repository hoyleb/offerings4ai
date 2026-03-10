from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import User
from app.schemas import (
    EmailVerificationRequest,
    EmailVerificationResponse,
    RegistrationResponse,
    ResendVerificationRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserPublic,
    VerificationDispatchResponse,
)
from app.services.auth import (
    authenticate_user,
    register_user,
    resend_verification_email,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=RegistrationResponse, status_code=201)
def register(payload: UserCreate, db: DbSession) -> RegistrationResponse:
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: DbSession) -> TokenResponse:
    token = authenticate_user(db, payload.email, payload.password)
    return TokenResponse(access_token=token)


@router.post("/verify-email", response_model=EmailVerificationResponse)
def verify_email(payload: EmailVerificationRequest, db: DbSession) -> EmailVerificationResponse:
    return verify_email_token(db, payload.token)


@router.get("/verify-email", response_model=EmailVerificationResponse)
def verify_email_from_link(
    db: DbSession,
    token: str = Query(min_length=16, max_length=255),
) -> EmailVerificationResponse:
    return verify_email_token(db, token)


@router.post("/resend-verification", response_model=VerificationDispatchResponse)
def resend_verification(
    payload: ResendVerificationRequest,
    db: DbSession,
) -> VerificationDispatchResponse:
    return resend_verification_email(db, payload)


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return current_user
