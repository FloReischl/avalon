"""Configured avatar asset endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.state import get_avalo_state
from app.user_config import resolve_avatar_asset_path


router = APIRouter(prefix="/assets/avatar", tags=["assets"])


@router.get("/images/{key}")
async def avatar_image(key: str) -> FileResponse:
    """Return one configured image of the effective avatar by logical key."""
    images = get_avalo_state().current_avatar.images

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

    path = resolve_avatar_asset_path(images.base_path, asset)
    return FileResponse(path)
