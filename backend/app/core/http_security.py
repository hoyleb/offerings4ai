from __future__ import annotations

import secrets
from dataclasses import dataclass

from fastapi import Request, Response
from fastapi.security.utils import get_authorization_scheme_param

from app.core.config import get_settings

SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_SAMESITE = "lax"


@dataclass(frozen=True)
class BrowserSessionTokens:
    access_token: str
    csrf_token: str


def build_browser_session_tokens(
    access_token: str,
    csrf_token: str | None = None,
) -> BrowserSessionTokens:
    return BrowserSessionTokens(
        access_token=access_token,
        csrf_token=csrf_token or secrets.token_urlsafe(32),
    )


def apply_session_cookies(response: Response, tokens: BrowserSessionTokens) -> None:
    settings = get_settings()
    max_age = settings.jwt_expire_minutes * 60
    cookie_kwargs = {
        "max_age": max_age,
        "path": SESSION_COOKIE_PATH,
        "samesite": SESSION_COOKIE_SAMESITE,
        "secure": settings.cookie_secure,
    }
    response.set_cookie(
        settings.session_cookie_name,
        tokens.access_token,
        httponly=True,
        **cookie_kwargs,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        tokens.csrf_token,
        httponly=False,
        **cookie_kwargs,
    )


def apply_csrf_cookie(response: Response, csrf_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        max_age=settings.jwt_expire_minutes * 60,
        path=SESSION_COOKIE_PATH,
        samesite=SESSION_COOKIE_SAMESITE,
        secure=settings.cookie_secure,
    )


def clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for cookie_name in (settings.session_cookie_name, settings.csrf_cookie_name):
        response.delete_cookie(
            cookie_name,
            path=SESSION_COOKIE_PATH,
            samesite=SESSION_COOKIE_SAMESITE,
            secure=settings.cookie_secure,
        )


def get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    scheme, credentials = get_authorization_scheme_param(authorization)
    if scheme.lower() != "bearer" or not credentials:
        return None
    return credentials
