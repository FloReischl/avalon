"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import assets, audio, chat, chats, health, tts, ui


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ui.router, prefix="/api/v1")
api_router.include_router(assets.router, prefix="/api/v1")
api_router.include_router(chat.router, prefix="/api/v1")

api_router.include_router(chats.router, prefix="/api/v1")
api_router.include_router(audio.router, prefix="/api/v1")
api_router.include_router(tts.router, prefix="/api/v1")

