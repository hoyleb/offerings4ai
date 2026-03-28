import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.http_security import (
    apply_csrf_cookie,
    apply_session_cookies,
    build_browser_session_tokens,
    clear_session_cookies,
)
from app.dependencies import get_current_user, get_db, get_optional_current_user
from app.models import User
from app.schemas import (
    AuthSessionResponse,
    CsrfTokenResponse,
    EmailVerificationRequest,
    EmailVerificationResponse,
    PasswordResetConfirm,
    PasswordResetDispatchResponse,
    PasswordResetRequest,
    PasswordResetResponse,
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
    complete_password_reset,
    register_user,
    request_password_reset,
    resend_verification_email,
    verify_email_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]


@router.post("/register", response_model=RegistrationResponse, status_code=201)
def register(payload: UserCreate, db: DbSession) -> RegistrationResponse:
    return register_user(db, payload)


@router.get("/csrf", response_model=CsrfTokenResponse)
def csrf_bootstrap(request: Request, response: Response) -> CsrfTokenResponse:
    settings = get_settings()
    csrf_token = request.cookies.get(settings.csrf_cookie_name) or secrets.token_urlsafe(32)
    apply_csrf_cookie(response, csrf_token)
    return CsrfTokenResponse(csrf_token=csrf_token)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: DbSession, request: Request, response: Response) -> TokenResponse:
    settings = get_settings()
    token = authenticate_user(db, payload.email, payload.password)
    apply_session_cookies(
        response,
        build_browser_session_tokens(
            token,
            request.cookies.get(settings.csrf_cookie_name),
        ),
    )
    return TokenResponse(access_token=token)


@router.get("/session", response_model=AuthSessionResponse)
def session(current_user: OptionalCurrentUser) -> AuthSessionResponse:
    registration_enabled = get_settings().registration_enabled
    if current_user is None:
        return AuthSessionResponse(
            is_authenticated=False,
            registration_enabled=registration_enabled,
        )
    return AuthSessionResponse(
        is_authenticated=True,
        registration_enabled=registration_enabled,
        user=current_user,
    )


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


@router.post("/request-password-reset", response_model=PasswordResetDispatchResponse)
def request_password_reset_route(
    payload: PasswordResetRequest,
    db: DbSession,
) -> PasswordResetDispatchResponse:
    return request_password_reset(db, payload)


@router.post("/reset-password", response_model=PasswordResetResponse)
def reset_password_route(
    payload: PasswordResetConfirm,
    db: DbSession,
    request: Request,
    response: Response,
) -> PasswordResetResponse:
    settings = get_settings()
    token = complete_password_reset(db, payload)
    apply_session_cookies(
        response,
        build_browser_session_tokens(
            token,
            request.cookies.get(settings.csrf_cookie_name),
        ),
    )
    return PasswordResetResponse(message="Password updated. You are now signed in.")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserPublic)
def me(current_user: CurrentUser) -> UserPublic:
    return current_user
