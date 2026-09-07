"""FastAPI application entry point."""

import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.persistence.migrations import run_migrations


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Prepare persistent state before serving requests."""
    del application

    try:
        run_migrations()
    except Exception as exc:
        print(f"Database initialization failed: {exc}", file=sys.stderr)
        raise

    yield


def create_app() -> FastAPI:
    """Create the backend application."""

    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Avalo-TTS-Playback-ID"],

    )
    application.include_router(api_router)
    return application


app = create_app()
