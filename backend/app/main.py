"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import LlmConfig, configure_logging, settings
from app.avatars_config import initialize_avatars_config
from app.models_config import initialize_models_config
from app.mcp.server import create_mcp_server
from app.mcp.security import current_principal_id, principal_from_authorization
from app.persistence.migrations import run_migrations
from app.persistence.authorization_repository import AuthorizationRepository
from app.persistence.database import create_database_engine, create_session_factory
from app.persistence.chat_repository import ChatRepository
from app.persistence.workflow_execution_repository import WorkflowExecutionRepository
from app.runtime.ollama import OllamaRuntime
from app.state import initialize_avalon_state
from app.user_config import initialize_user_config
from app.user_settings import initialize_user_settings
from app.agents_config import load_agents_config
from app.workflows_config import initialize_workflows_config
from app.services.workflows import WorkflowService


logger = logging.getLogger(__name__)


async def validate_configured_llms(
    runtime: OllamaRuntime,
    llm_models: tuple[LlmConfig, ...],
) -> None:
    """Validate configured Ollama models required by this process."""
    standard = next(
        llm for llm in llm_models if llm.key == "standard"
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

    for llm in llm_models:
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
    async with application.state.mcp.session_manager.run():
        try:
            user_config = initialize_user_config()
            user_settings = initialize_user_settings()
            avatars_config = initialize_avatars_config()
            models_config = initialize_models_config()
            agents_config = load_agents_config()
            initialize_workflows_config()
            initialize_avalon_state(
                user_config,
                avatars_config,
                models_config,
                agents_config,
            )

            await validate_configured_llms(OllamaRuntime(), models_config.llm_models)
            run_migrations()
            engine = create_database_engine()
            try:
                repository = AuthorizationRepository(create_session_factory(engine))
                repository.reconcile_chat_permissions(user_config.chat)
                repository.reconcile_agents_permissions(agents_config)
            finally:
                engine.dispose()
        except Exception:
            logger.exception("[startup] backend initialization failed")
            raise

        try:
            yield
        finally:
            application.state.workflow_engine.dispose()


class StderrExceptionMiddleware:
    """Log uncaught backend exceptions with their full traceback."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        try:
            await self.app(scope, receive, send)
        except Exception:
            logger.exception("[unhandled] uncaught exception in request handler")
            raise


class PrincipalBearerMiddleware:
    """Resolve the local bearer token for mounted MCP requests."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/mcp"):
            await self.app(scope, receive, send)
            return
        try:
            authorization = dict(scope["headers"]).get(b"authorization", b"").decode("ascii")
            principal_id = principal_from_authorization(authorization)
        except (HTTPException, UnicodeDecodeError) as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else "Invalid bearer token."
            await JSONResponse({"detail": detail}, status_code=401)(scope, receive, send)
            return
        token = current_principal_id.set(principal_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_principal_id.reset(token)


async def require_api_principal(request: Request) -> None:
    """Resolve the bearer principal for API routes where identity matters."""
    path = request.url.path
    if not path.startswith("/api/v1/") or path in {"/api/v1/ui/config", "/api/v1/ui/token", "/api/v1/ui/settings"} or path.startswith("/api/v1/assets/avatar/") or (path.endswith("/download") and path.startswith("/api/v1/attachments/")) or path in {"/api/v1/authorization-requests/events", "/api/v1/workflow-executions/events"}:
        return
    principal_id = principal_from_authorization(request.headers.get("Authorization"))
    request.scope["avalon.principal_id"] = principal_id


def create_app() -> FastAPI:
    """Create the backend application."""
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        dependencies=[Depends(require_api_principal)],
    )
    application.add_middleware(PrincipalBearerMiddleware)
    application.add_middleware(StderrExceptionMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_dev_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["X-Avalon-TTS-Playback-ID"],

    )
    application.include_router(api_router)
    workflow_engine = create_database_engine()
    workflow_session_factory = create_session_factory(workflow_engine)
    mcp = create_mcp_server(
        workflow_service=WorkflowService(
            repository=WorkflowExecutionRepository(workflow_session_factory),
            chat_repository=ChatRepository(workflow_session_factory),
        )
    )
    application.state.workflow_engine = workflow_engine
    application.state.mcp = mcp
    application.mount(
        "/mcp",
        mcp.streamable_http_app(
            streamable_http_path="/",
            host=settings.api_host,
        ),
    )
    return application


app = create_app()
