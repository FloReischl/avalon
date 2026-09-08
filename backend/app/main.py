"""FastAPI application entry point."""

import sys
import traceback
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
    except Exception:
        traceback.print_exc(file=sys.stderr)
        raise

    yield


class StderrExceptionMiddleware:
    """Write uncaught backend exceptions with their full traceback to stderr."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        try:
            await self.app(scope, receive, send)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            raise


def create_app() -> FastAPI:
    """Create the backend application."""

    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(StderrExceptionMiddleware)
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
