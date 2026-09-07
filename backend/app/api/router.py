"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import audio, chat, chats, health, tts

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chat.router, prefix="/api/v1")
api_router.include_router(chats.router, prefix="/api/v1")
api_router.include_router(audio.router, prefix="/api/v1")
api_router.include_router(tts.router, prefix="/api/v1")

