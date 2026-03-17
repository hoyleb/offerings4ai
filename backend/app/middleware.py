from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.http_security import get_bearer_token
from app.services.request_limits import choose_rate_limit_policy, enforce_rate_limit

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method.upper() not in STATE_CHANGING_METHODS:
            return await call_next(request)

        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        if get_bearer_token(request):
            return await call_next(request)

        settings = get_settings()
        csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
        csrf_header = request.headers.get(settings.csrf_header_name)
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        "CSRF validation failed. Refresh the page and retry the request from a "
                        "trusted browser session."
                    )
                },
            )

        return await call_next(request)


class RuntimeHardeningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if settings.https_redirect_enabled and not _request_is_secure(request):
            if request.method.upper() in {"GET", "HEAD"}:
                https_url = request.url.replace(scheme="https")
                return RedirectResponse(str(https_url), status_code=307)
            return JSONResponse(status_code=400, content={"detail": "HTTPS is required."})

        policy = choose_rate_limit_policy(request)
        if policy is not None:
            decision = enforce_rate_limit(request, policy)
            if not decision.allowed:
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(decision.retry_after_seconds)},
                    content={"detail": "Rate limit exceeded. Retry later."},
                )

        response = await call_next(request)
        if settings.security_headers_enabled:
            _apply_security_headers(response, request)
        return response


def _request_is_secure(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    first_proto = forwarded_proto.split(",")[0].strip().lower()
    if first_proto == "https":
        return True
    host = request.url.hostname or ""
    return host in {"localhost", "127.0.0.1"}


def _apply_security_headers(response: Response, request: Request) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), geolocation=(), microphone=()")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if request.url.path.startswith("/api/auth/"):
        response.headers.setdefault("Cache-Control", "no-store")
