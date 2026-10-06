"""Frontend-specific runtime configuration endpoint."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.schemas import (
    UiAnimationResponse,
    UiAvatarResponse,
    UiConfigResponse,
    AgentTokenResponse,
    UiSpriteRegionResponse,
    UiStandardImageResponse,
    UserSettingsUpdateRequest,
)
from app.state import get_avalon_state
from app.user_settings import get_user_settings, save_user_settings
from app.persistence.authorization_repository import AuthorizationRepository
from app.api.routes.chats import get_authorization_repository
from app.mcp.security import bearer_token_for_agent


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
    agent = repository.get_agent_by_key(state.user_config.chat_default_agent_key)
    if agent is None:
        raise RuntimeError("Configured default chat agent does not exist.")
    agent_token = bearer_token_for_agent(agent.id)

    return UiConfigResponse(
        name=state.user_config.name,
        agentBearerToken=agent_token,
        avatarZoom=get_user_settings().avatar_zoom,
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


@router.get("/token", response_model=AgentTokenResponse)
async def ui_agent_token(
    agent_id: int = Query(gt=0),
    repository: AuthorizationRepository = Depends(get_authorization_repository),
) -> AgentTokenResponse:
    """Return a fresh local bearer token for one persisted agent."""
    if repository.get_agent_by_id(agent_id) is None:
        raise HTTPException(status_code=404, detail="Agent does not exist.")
    return AgentTokenResponse(
        agentBearerToken=bearer_token_for_agent(agent_id)
    )


@router.put("/settings")
async def update_user_settings(body: UserSettingsUpdateRequest) -> dict:
    """Update user settings (e.g. avatar zoom)."""
    zoom = body.avatar_zoom if body.avatar_zoom is not None else body.avatarZoom
    if zoom is None:
        raise ValueError("avatar_zoom or avatarZoom is required.")
    save_user_settings(zoom)
    return {"status": "ok", "avatar_zoom": zoom}
