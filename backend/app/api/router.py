"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import attachments, authorization, assets, audio, chat, chats, health, runtime, tts, ui, workflows


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ui.router, prefix="/api/v1")
api_router.include_router(assets.router, prefix="/api/v1")
api_router.include_router(chat.router, prefix="/api/v1")
api_router.include_router(authorization.router, prefix="/api/v1")

api_router.include_router(chats.router, prefix="/api/v1")
api_router.include_router(attachments.router, prefix="/api/v1")
api_router.include_router(audio.router, prefix="/api/v1")
api_router.include_router(runtime.router, prefix="/api/v1")
api_router.include_router(tts.router, prefix="/api/v1")
api_router.include_router(workflows.router, prefix="/api/v1")
