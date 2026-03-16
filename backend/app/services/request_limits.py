from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock

from fastapi import Request
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import get_settings


@dataclass(frozen=True)
class RateLimitPolicy:
    bucket: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int


class InMemoryLimiter:
    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            queue = self._events[key]
            while queue and queue[0] <= cutoff:
                queue.popleft()
            if len(queue) >= limit:
                retry_after = max(1, int(window_seconds - (now - queue[0])))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
            queue.append(now)
        return RateLimitDecision(allowed=True, retry_after_seconds=window_seconds)


class RedisBackedLimiter:
    def __init__(self, redis_factory: Callable[[], Redis]) -> None:
        self._redis_factory = redis_factory

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        now = int(time.time())
        window_bucket = now // window_seconds
        redis_key = f"rate-limit:{key}:{window_bucket}"
        client = self._redis_factory()
        count = client.incr(redis_key)
        if count == 1:
            client.expire(redis_key, window_seconds + 1)
        if count > limit:
            retry_after = max(1, window_seconds - (now % window_seconds))
            return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)
        return RateLimitDecision(allowed=True, retry_after_seconds=window_seconds)


_memory_limiter = InMemoryLimiter()
_redis_client: Redis | None = None


def choose_rate_limit_policy(request: Request) -> RateLimitPolicy | None:
    settings = get_settings()
    if not settings.rate_limit_enabled:
        return None

    path = request.url.path
    method = request.method.upper()
    if path.startswith("/api/auth/") and method in {"POST", "PUT", "PATCH", "DELETE"}:
        return RateLimitPolicy(
            bucket="auth",
            limit=settings.auth_rate_limit_count,
            window_seconds=settings.auth_rate_limit_window_seconds,
        )

    if path.startswith("/api/ideas") and method in {"POST", "PUT", "PATCH", "DELETE"}:
        return RateLimitPolicy(
            bucket="ideas-write",
            limit=settings.write_rate_limit_count,
            window_seconds=settings.write_rate_limit_window_seconds,
        )

    if path == "/api/public/ideas/feed" and method == "GET":
        return RateLimitPolicy(
            bucket="public-feed",
            limit=settings.public_feed_rate_limit_count,
            window_seconds=settings.public_feed_rate_limit_window_seconds,
        )

    return None


def enforce_rate_limit(request: Request, policy: RateLimitPolicy) -> RateLimitDecision:
    identity = _request_identity(request)
    key = f"{policy.bucket}:{identity}"
    limiter = _redis_or_memory_limiter()
    try:
        return limiter.check(key, policy.limit, policy.window_seconds)
    except RedisError:
        return _memory_limiter.check(key, policy.limit, policy.window_seconds)


def _request_identity(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _redis_or_memory_limiter() -> RedisBackedLimiter | InMemoryLimiter:
    settings = get_settings()
    if not settings.redis_url:
        return _memory_limiter

    return RedisBackedLimiter(_redis_client_factory)


def _redis_client_factory() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(get_settings().redis_url, socket_timeout=0.25)
    return _redis_client
