"""Tests for the frontend-specific runtime configuration contract."""

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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


def assert_avatar_asset_url(
    url: str,
    expected_path: str,
) -> str:
    parsed = urlsplit(url)

    assert parsed.scheme == "http"
    assert parsed.netloc == "test"
    assert parsed.path == expected_path

    query = parse_qs(parsed.query)
    assert set(query) == {"v"}
    assert len(query["v"]) == 1
    assert query["v"][0]

    return query["v"][0]


def test_ui_config_exposes_only_frontend_runtime_data() -> None:
    initialize_blueprint_config()

    response = request("/api/v1/ui/config")

    assert response.status_code == 200
    payload = response.json()

    assert payload["name"] == "Frieda"
    assert payload["avatar"]["standard"]["key"] == "standard"

    cache_token = assert_avatar_asset_url(
        payload["avatar"]["standard"]["url"],
        "/api/v1/assets/avatar/images/standard",
    )

    assert assert_avatar_asset_url(
        payload["avatar"]["greetingAudioUrl"],
        "/api/v1/assets/avatar/greeting",
    ) == cache_token

    assert payload["avatar"]["animations"]

    for animation in payload["avatar"]["animations"]:
        assert set(animation) == {
            "key",
            "category",
            "spriteSetUrl",
            "sprites",
        }
        assert assert_avatar_asset_url(
            animation["spriteSetUrl"],
            f"/api/v1/assets/avatar/images/{animation['key']}",
        ) == cache_token
        for sprite in animation["sprites"]:
            assert set(sprite) == {
                "x",
                "y",
                "width",
                "height",
            }

    serialized = response.text
    assert "persona" not in serialized
    assert "instructions" not in serialized
    assert "base_path" not in serialized
    assert "kokoro" not in serialized
    assert "chatterbox" not in serialized


def test_ui_config_keeps_avatar_cache_token_stable() -> None:
    initialize_blueprint_config()

    first_response = request("/api/v1/ui/config")
    second_response = request("/api/v1/ui/config")

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_token = assert_avatar_asset_url(
        first_response.json()["avatar"]["standard"]["url"],
        "/api/v1/assets/avatar/images/standard",
    )
    second_token = assert_avatar_asset_url(
        second_response.json()["avatar"]["standard"]["url"],
        "/api/v1/assets/avatar/images/standard",
    )

    assert second_token == first_token


def test_ui_config_uses_current_avatar() -> None:
    initialize_blueprint_config()
    standard = state_module.get_avalon_state().current_avatar
    reversed_images = standard.images.model_copy(
        update={
            "animations": list(reversed(standard.images.animations)),
        },
        deep=True,
    )
    second = standard.model_copy(
        update={
            "key": "second",
            "images": reversed_images,
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

    response = request("/api/v1/ui/config")

    assert response.status_code == 200
    assert response.json()["avatar"]["animations"][0]["key"] == (
        reversed_images.animations[0].key
    )


def test_ui_config_exposes_custom_animations() -> None:
    initialize_blueprint_config()

    response = request("/api/v1/ui/config")

    assert response.status_code == 200
    animations = response.json()["avatar"]["animations"]

    custom = [
        animation
        for animation in animations
        if animation["category"] == "custom"
    ]

    assert custom
    assert all(animation["key"] != "standard" for animation in animations)
