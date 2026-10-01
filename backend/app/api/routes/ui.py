"""Frontend-specific runtime configuration endpoint."""

from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.api.schemas import (
    UiAnimationResponse,
    UiAvatarResponse,
    UiConfigResponse,
    UiSpriteRegionResponse,
    UiStandardImageResponse,
)
from app.state import get_avalon_state
from app.persistence.authorization_repository import AuthorizationRepository
from app.api.routes.chats import get_authorization_repository
from app.mcp.security import bearer_token_for_principal


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
async def ui_config(
    request: Request,
    repository: AuthorizationRepository = Depends(get_authorization_repository),
) -> UiConfigResponse:
    """Return only configuration intentionally exposed to the frontend."""
    state = get_avalon_state()
    avatar = state.current_avatar
    principal = repository.get_principal_by_key(state.user_config.chat_default_principal_key)
    if principal is None:
        raise RuntimeError("Configured default chat principal does not exist.")
    principal_token = bearer_token_for_principal(principal.id)

    return UiConfigResponse(
        name=state.user_config.name,
        principalBearerToken=principal_token,
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
