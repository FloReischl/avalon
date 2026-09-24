"""Tests for configured avatar image delivery."""

import asyncio
import logging
from pathlib import Path

from httpx import ASGITransport, AsyncClient

import app.state as state_module
import app.user_config as user_config_module
from app.main import create_app
from app.state import initialize_avalon_state
from app.user_config import initialize_user_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT_CONFIG = (
    PROJECT_ROOT
    / "data"
    / "blueprints"
    / "user.avalon"
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
    state_module._avalon_state = None
    config = initialize_user_config(BLUEPRINT_CONFIG)
    initialize_avalon_state(config)


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


def test_avatar_assets_use_current_avatar() -> None:
    initialize_blueprint_config()
    standard = state_module.get_avalon_state().current_avatar
    alternate_asset = standard.images.animations[0].sprite_set
    alternate_images = standard.images.model_copy(
        update={"standard": alternate_asset},
        deep=True,
    )
    second = standard.model_copy(
        update={
            "key": "second",
            "images": alternate_images,
        },
        deep=True,
    )
    config = user_config_module.get_user_config().model_copy(
        update={
            "avatars": [
                standard,
                second,
            ]
        },
        deep=True,
    )

    state_module._avalon_state = None
    state = initialize_avalon_state(config)
    assert state.set_current_avatar("second") is True

    expected = (
        second.base_path / alternate_asset
    ).resolve().read_bytes()

    response = request("/api/v1/assets/avatar/images/standard")

    assert response.status_code == 200
    assert response.content == expected


def test_avatar_greeting_is_served_from_current_avatar() -> None:
    initialize_blueprint_config()
    standard = state_module.get_avalon_state().current_avatar
    second = standard.model_copy(
        update={
            "key": "second",
            "greeting_audio": standard.images.standard,
        },
        deep=True,
    )
    config = user_config_module.get_user_config().model_copy(
        update={
            "avatars": [
                standard,
                second,
            ]
        },
        deep=True,
    )

    state_module._avalon_state = None
    state = initialize_avalon_state(config)
    assert state.set_current_avatar("second") is True

    expected = (
        second.base_path / second.greeting_audio
    ).resolve().read_bytes()

    response = request("/api/v1/assets/avatar/greeting")

    assert response.status_code == 200
    assert response.content == expected


def test_missing_avatar_greeting_returns_not_found_and_logs(
    caplog,
) -> None:
    initialize_blueprint_config()
    config = user_config_module.get_user_config()
    standard = config.standard_avatar.model_copy(
        update={"greeting_audio": "missing-greeting.wav"},
        deep=True,
    )
    updated = config.model_copy(
        update={
            "avatars": [
                standard if avatar.key == "standard" else avatar
                for avatar in config.avatars
            ]
        },
        deep=True,
    )

    state_module._avalon_state = None
    initialize_avalon_state(updated)

    with caplog.at_level(logging.ERROR):
        response = request("/api/v1/assets/avatar/greeting")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Avatar greeting audio not found.",
    }
    assert "[avatar-assets] greeting audio unavailable" in caplog.text


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