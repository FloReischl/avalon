"""Tests for the frontend-specific runtime configuration contract."""

import asyncio
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

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
