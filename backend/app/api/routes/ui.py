"""Frontend-specific runtime configuration endpoint."""

from uuid import uuid4

from fastapi import APIRouter, Request

from app.api.schemas import (
    UiAnimationResponse,
    UiAvatarResponse,
    UiConfigResponse,
    UiSpriteRegionResponse,
    UiStandardImageResponse,
)
from app.state import get_avalon_state


router = APIRouter(prefix="/ui", tags=["ui"])

_AVATAR_ASSET_CACHE_TOKEN = uuid4().hex


def _absolute_url(request: Request, path: str) -> str:
    return str(request.base_url).rstrip("/") + path


def _avatar_asset_url(
    request: Request,
    path: str,
    avatar_key: str,
) -> str:
    return (
        f"{_absolute_url(request, path)}"
        f"?v={_AVATAR_ASSET_CACHE_TOKEN}-{avatar_key}"
    )


@router.get("/config", response_model=UiConfigResponse)
async def ui_config(request: Request) -> UiConfigResponse:
    """Return only configuration intentionally exposed to the frontend."""
    state = get_avalon_state()
    avatar = state.current_avatar

    return UiConfigResponse(
        name=state.user_config.name,
        avatar=UiAvatarResponse(
            greetingAudioUrl=_avatar_asset_url(
                request,
                "/api/v1/assets/avatar/greeting",
                avatar.key,
            ),
            standard=UiStandardImageResponse(
                url=_avatar_asset_url(
                    request,
                    "/api/v1/assets/avatar/images/standard",
                    avatar.key,
                ),
            ),
            animations=[
                UiAnimationResponse(
                    key=animation.key,
                    category=animation.category,
                    spriteSetUrl=_avatar_asset_url(
                        request,
                        f"/api/v1/assets/avatar/images/{animation.key}",
                        avatar.key,
                    ),
                    sprites=[
                        UiSpriteRegionResponse(
                            x=sprite.x,
                            y=sprite.y,
                            width=sprite.width,
                            height=sprite.height,
                        )
                        for sprite in animation.sprites
                    ],
                )
                for animation in avatar.images.animations
            ],
        ),
    )
