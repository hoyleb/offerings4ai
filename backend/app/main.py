from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import auth, health, ideas, public
from app.core.config import get_settings
from app.db import ensure_current_schema
from app.mcp_server import mcp_server
from app.middleware import CsrfProtectionMiddleware, RuntimeHardeningMiddleware

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    ensure_current_schema()
    yield


app = FastAPI(
    title="Offering4AI API",
    version="0.2.0",
    description=(
        "Machine-readable API for structured human idea submissions, public discovery surfaces, "
        "evaluation logs, and AI agent integration."
    ),
    lifespan=lifespan,
)

app.add_middleware(RuntimeHardeningMiddleware)
app.add_middleware(CsrfProtectionMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials="*" not in settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.mount("/mcp", mcp_server.sse_app())
