from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, health, ideas, public
from app.core.config import get_settings
from app.db import create_db_and_tables
from app.mcp_server import mcp_server

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    create_db_and_tables()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins or ["*"],
    allow_credentials="*" not in settings.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public.router)
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.mount("/mcp", mcp_server.sse_app())
