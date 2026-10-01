from pathlib import Path
import pytest
import yaml

import app.user_settings as user_settings_module
from app.user_settings import (
    load_user_settings,
    save_user_settings,
    UserSettings,
)


def test_missing_file_uses_default_zoom(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings = load_user_settings(settings_path)
    assert settings.avatar_zoom == 1.0


def test_missing_key_uses_default_zoom(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text("other_setting: true\n", encoding="utf-8")

    settings = load_user_settings(settings_path)
    assert settings.avatar_zoom == 1.0


def test_valid_saved_value_is_loaded(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text("avatar_zoom: 1.25\n", encoding="utf-8")

    settings = load_user_settings(settings_path)
    assert settings.avatar_zoom == 1.25


def test_syntax_error_is_fatal(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text("avatar_zoom: [", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        load_user_settings(settings_path)
    assert exc_info.value.code == 1


def test_wrong_type_is_fatal(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text("avatar_zoom: 'large'\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        load_user_settings(settings_path)
    assert exc_info.value.code == 1


def test_out_of_range_zoom_is_fatal(tmp_path: Path) -> None:
    for invalid_zoom in [0.4, 1.6, 2.0]:
        settings_path = tmp_path / "user-settings.yaml"
        settings_path.write_text(f"avatar_zoom: {invalid_zoom}\n", encoding="utf-8")

        with pytest.raises(SystemExit) as exc_info:
            load_user_settings(settings_path)
        assert exc_info.value.code == 1


def test_zoom_change_is_persisted(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    save_user_settings(1.2, settings_path)

    data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert data["avatar_zoom"] == 1.2


def test_existing_other_user_settings_remain_intact_when_writing(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text(
        yaml.safe_dump({"other_key": "preserved", "avatar_zoom": 1.0}),
        encoding="utf-8",
    )

    save_user_settings(1.4, settings_path)

    data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert data["avatar_zoom"] == 1.4
    assert data["other_key"] == "preserved"


def test_saving_with_syntax_error_raises_error(tmp_path: Path) -> None:
    settings_path = tmp_path / "user-settings.yaml"
    settings_path.write_text("avatar_zoom: [", encoding="utf-8")

    with pytest.raises(yaml.YAMLError):
        save_user_settings(1.2, settings_path)


def test_ui_settings_api_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    from httpx import ASGITransport, AsyncClient
    from app.main import create_app

    settings_path = tmp_path / "user-settings.yaml"
    monkeypatch.setattr(user_settings_module, "USER_SETTINGS_PATH", settings_path)
    user_settings_module._user_settings = None

    async def run_test():
        application = create_app()
        transport = ASGITransport(app=application)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.put(
                "/api/v1/ui/settings",
                json={"avatarZoom": 1.35},
            )
            assert response.status_code == 200
            assert response.json() == {"status": "ok", "avatar_zoom": 1.35}

            data = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
            assert data["avatar_zoom"] == 1.35

    asyncio.run(run_test())
