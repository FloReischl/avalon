"""FastAPI application entry point."""

import logging
import sys
import traceback
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.persistence.migrations import run_migrations
from app.runtime.ollama import OllamaRuntime
from app.state import initialize_avalo_state
from app.user_config import initialize_user_config


logger = logging.getLogger(__name__)


async def validate_configured_llms(runtime: OllamaRuntime) -> None:
    """Validate configured Ollama models required by this process."""
    standard = next(
        llm for llm in settings.llm_models if llm.key == "standard"
    )

    if not await runtime.model_exists(standard.model):
        logger.error(
            "[startup] required LLM '%s' is unavailable: %s",
            standard.key,
            standard.model,
        )
        raise RuntimeError(
            f"Required LLM '{standard.key}' is unavailable: {standard.model}"
        )

    for llm in settings.llm_models:
        if llm.key == "standard":
            continue

        if not await runtime.model_exists(llm.model):
            logger.warning(
                "[startup] optional LLM '%s' is unavailable: %s",
                llm.key,
                llm.model,
            )


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Prepare persistent state before serving requests."""
    del application

    try:
        user_config = initialize_user_config()
        initialize_avalo_state(user_config)
        await validate_configured_llms(OllamaRuntime())
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
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
        expose_headers=["X-Avalo-TTS-Playback-ID"],

    )
    application.include_router(api_router)
    return application


app = create_app()
