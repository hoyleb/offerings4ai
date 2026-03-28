from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import User
from app.schemas import (
    EmailVerificationResponse,
    PasswordResetConfirm,
    PasswordResetDispatchResponse,
    PasswordResetRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    UserCreate,
    VerificationDispatchResponse,
)
from app.services.email import send_email


def register_user(db: Session, payload: UserCreate) -> RegistrationResponse:
    settings = get_settings()
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Registration is temporarily disabled until outbound verification email "
                "delivery is configured."
            ),
        )

    existing_user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing_user:
        if existing_user.email_verified_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Email already registered. Request another verification email to finish setup."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        payout_address=payload.payout_address,
    )
    db.add(user)

    dispatch = _issue_and_send_verification_email(user)
    db.commit()
    db.refresh(user)

    return RegistrationResponse(
        user=user,
        message=_registration_message(),
        debug_verify_url=dispatch.debug_verify_url,
        debug_verify_token=dispatch.debug_verify_token,
    )


def authenticate_user(db: Session, email: str, password: str) -> str:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.email_verified_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email address before logging in",
        )
    return create_access_token(str(user.id))


def verify_email_token(db: Session, token: str) -> EmailVerificationResponse:
    user = db.scalar(
        select(User).where(User.email_verification_token_hash == _hash_verification_token(token))
    )
    if user is None or user.email_verification_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link is invalid or has already been used",
        )
    if _as_utc(user.email_verification_expires_at) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification link has expired. Request a new one from the login form.",
        )

    user.email_verified_at = datetime.now(UTC)
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.add(user)
    db.commit()

    return EmailVerificationResponse(
        message="Email confirmed. You can now log in and submit ideas."
    )


def resend_verification_email(
    db: Session,
    payload: ResendVerificationRequest,
) -> VerificationDispatchResponse:
    settings = get_settings()
    if not settings.registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Verification email resend is temporarily disabled until outbound email "
                "delivery is configured."
            ),
        )

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or user.email_verified_at is not None:
        return VerificationDispatchResponse(
            message=(
                "If that address is pending verification, a fresh confirmation email is on its way."
            )
        )

    dispatch = _issue_and_send_verification_email(user)
    db.commit()
    db.refresh(user)

    return VerificationDispatchResponse(
        message=_resend_message(),
        debug_verify_url=dispatch.debug_verify_url,
        debug_verify_token=dispatch.debug_verify_token,
    )


def request_password_reset(
    db: Session,
    payload: PasswordResetRequest,
) -> PasswordResetDispatchResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or user.email_verified_at is None:
        return PasswordResetDispatchResponse(message=_password_reset_request_message())

    dispatch = _issue_and_send_password_reset_email(user)
    db.commit()

    return PasswordResetDispatchResponse(
        message=_password_reset_request_message(),
        debug_reset_url=dispatch.debug_reset_url,
        debug_reset_token=dispatch.debug_reset_token,
    )


def complete_password_reset(db: Session, payload: PasswordResetConfirm) -> str:
    user = db.scalar(
        select(User).where(
            User.password_reset_token_hash == _hash_verification_token(payload.token)
        )
    )
    if user is None or user.password_reset_expires_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link is invalid or has already been used",
        )
    if _as_utc(user.password_reset_expires_at) < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset link has expired. Request a fresh one from the sign-in form.",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    _clear_password_reset_state(user)
    db.add(user)
    db.commit()

    return create_access_token(str(user.id))


def _issue_and_send_verification_email(user: User) -> VerificationDispatchResponse:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.email_verify_token_expire_minutes)
    verify_url = _build_verification_url(raw_token)

    user.email_verification_token_hash = _hash_verification_token(raw_token)
    user.email_verification_sent_at = datetime.now(UTC)
    user.email_verification_expires_at = expires_at
    user.email_verified_at = None

    send_email(
        recipient=user.email,
        subject="Confirm your Offering4AI email address",
        text_body=(
            f"Hi {user.full_name},\n\n"
            "Confirm your email address before you can log in or submit ideas.\n\n"
            f"Verification link: {verify_url}\n\n"
            f"This link expires in {settings.email_verify_token_expire_minutes} minutes.\n"
        ),
    )

    if settings.app_env.lower() == "production":
        return VerificationDispatchResponse(message="Verification email sent.")

    return VerificationDispatchResponse(
        message="Verification email sent.",
        debug_verify_url=verify_url,
        debug_verify_token=raw_token,
    )


def _issue_and_send_password_reset_email(user: User) -> PasswordResetDispatchResponse:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_expire_minutes)
    reset_url = _build_password_reset_url(raw_token)

    user.password_reset_token_hash = _hash_verification_token(raw_token)
    user.password_reset_sent_at = datetime.now(UTC)
    user.password_reset_expires_at = expires_at

    send_email(
        recipient=user.email,
        subject="Reset your Offering4AI password",
        text_body=(
            f"Hi {user.full_name},\n\n"
            "Use the link below to choose a new Offering4AI password.\n\n"
            f"Password reset link: {reset_url}\n\n"
            f"This link expires in {settings.password_reset_token_expire_minutes} minutes.\n"
        ),
    )

    if settings.app_env.lower() == "production":
        return PasswordResetDispatchResponse(message=_password_reset_request_message())

    return PasswordResetDispatchResponse(
        message=_password_reset_request_message(),
        debug_reset_url=reset_url,
        debug_reset_token=raw_token,
    )


def _hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC)
    return value.replace(tzinfo=UTC)


def _build_verification_url(token: str) -> str:
    settings = get_settings()
    if settings.public_site_url:
        query = urlencode({"verify_email_token": token})
        return f"{settings.public_site_url.rstrip('/')}/?{query}"

    if settings.public_api_base_url:
        base_url = settings.public_api_base_url.rstrip("/")
    else:
        base_url = f"http://localhost:{settings.app_port}"

    query = urlencode({"token": token})
    return f"{base_url}/api/auth/verify-email?{query}"


def _build_password_reset_url(token: str) -> str:
    settings = get_settings()
    if settings.public_site_url:
        query = urlencode({"reset_password_token": token})
        return f"{settings.public_site_url.rstrip('/')}/?{query}"

    query = urlencode({"reset_password_token": token})
    return f"http://localhost:5188/?{query}"


def _clear_password_reset_state(user: User) -> None:
    user.password_reset_token_hash = None
    user.password_reset_sent_at = None
    user.password_reset_expires_at = None


def _registration_message() -> str:
    settings = get_settings()
    if settings.email_delivery_mode.lower().strip() == "smtp":
        return (
            "Account created. Check your email to verify your address before logging in or "
            "submitting ideas."
        )

    return (
        "Account created. This environment is using local log mode, so no inbox email will "
        "arrive. Use the development verify button below or switch EMAIL_DELIVERY_MODE=smtp."
    )


def _resend_message() -> str:
    settings = get_settings()
    if settings.email_delivery_mode.lower().strip() == "smtp":
        return "If that address is pending verification, a fresh confirmation email is on its way."

    return (
        "If that address is pending verification, this environment is using local log mode. "
        "Use the development verify button below or switch EMAIL_DELIVERY_MODE=smtp."
    )


def _password_reset_request_message() -> str:
    return "If that address belongs to a verified account, a password reset link is on its way."
