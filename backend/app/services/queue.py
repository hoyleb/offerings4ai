from __future__ import annotations

from redis import Redis
from rq import Queue

from app.core.config import get_settings


def get_redis() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)


def get_queue() -> Queue:
    return Queue("idea-evaluations", connection=get_redis())
