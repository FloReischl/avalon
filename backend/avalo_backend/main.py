"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from avalo_backend.api.router import api_router
from avalo_backend.config import settings


def create_app() -> FastAPI:
    """Create the backend application."""

    application = FastAPI(title=settings.app_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(api_router)
    return application


app = create_app()
