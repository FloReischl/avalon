"""Tests for configured avatar image delivery."""

import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

import app.user_config as user_config_module
from app.main import create_app
from app.user_config import initialize_user_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "blueprints"
    / "user.avalo"
    / "config.yaml"
)


def request(path: str):
    async def send_request():
        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            return await client.get(path)

    return asyncio.run(send_request())


def initialize_blueprint_config() -> None:
    user_config_module._user_config = None
    initialize_user_config(BLUEPRINT_CONFIG)


def test_standard_avatar_image_is_served() -> None:
    initialize_blueprint_config()

    response = request("/api/v1/assets/avatar/images/standard")

    assert response.status_code == 200
    assert response.content


def test_configured_animation_image_is_served() -> None:
    initialize_blueprint_config()
    animation_key = (
        user_config_module.get_user_config()
        .standard_avatar
        .images
        .animations[0]
        .key
    )

    response = request(
        f"/api/v1/assets/avatar/images/{animation_key}"
    )

    assert response.status_code == 200
    assert response.content


def test_unknown_avatar_image_returns_not_found() -> None:
    initialize_blueprint_config()

    response = request(
        "/api/v1/assets/avatar/images/definitely-not-configured"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Avatar image not found.",
    }


def test_path_like_avatar_key_cannot_access_files() -> None:
    initialize_blueprint_config()

    response = request(
        "/api/v1/assets/avatar/images/%2E%2E%2Fconfig.yaml"
    )

    assert response.status_code == 404