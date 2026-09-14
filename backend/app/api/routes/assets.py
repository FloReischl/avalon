"""Configured avatar asset endpoints."""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.state import get_avalo_state
from app.user_config import resolve_avatar_asset_path


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets/avatar", tags=["assets"])


@router.get("/images/{key}")
async def avatar_image(key: str) -> FileResponse:
    """Return one configured image of the effective avatar by logical key."""
    avatar = get_avalo_state().current_avatar
    images = avatar.images

    if key == "standard":
        asset = images.standard
    else:
        animation = next(
            (
                animation
                for animation in images.animations
                if animation.key == key
            ),
            None,
        )
        if animation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Avatar image not found.",
            )
        asset = animation.sprite_set

    path = resolve_avatar_asset_path(avatar.base_path, asset)
    return FileResponse(path)


@router.get("/greeting")
async def avatar_greeting_audio() -> FileResponse:
    """Return the configured greeting audio of the effective avatar."""
    avatar = get_avalo_state().current_avatar

    try:
        path = resolve_avatar_asset_path(
            avatar.base_path,
            avatar.greeting_audio,
        )
    except ValueError as exc:
        logger.exception("[avatar-assets] greeting audio unavailable")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Avatar greeting audio not found.",
        ) from exc

    return FileResponse(path)
