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
    RegistrationResponse,
    ResendVerificationRequest,
    UserCreate,
    VerificationDispatchResponse,
)
from app.services.email import send_email


def register_user(db: Session, payload: UserCreate) -> RegistrationResponse:
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
        message=(
            "Account created. Check your email to verify your address before logging in or "
            "submitting ideas."
        ),
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
        message=(
            "If that address is pending verification, a fresh confirmation email is on its way."
        ),
        debug_verify_url=dispatch.debug_verify_url,
        debug_verify_token=dispatch.debug_verify_token,
    )


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
