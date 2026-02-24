from __future__ import annotations

from unittest.mock import patch

from pylibrelinkup import APIUrl


def test_settings_loads_from_env() -> None:
    with patch.dict(
        "os.environ",
        {"LIBRE_EMAIL": "a@b.com", "LIBRE_PASSWORD": "pw", "LIBRE_REGION": "EU"},
    ):
        from app.config import Settings

        s = Settings()
        assert s.libre_email == "a@b.com"
        assert s.libre_password == "pw"
        assert s.libre_region == "EU"


def test_api_url_property() -> None:
    with patch.dict(
        "os.environ",
        {"LIBRE_EMAIL": "a@b.com", "LIBRE_PASSWORD": "pw", "LIBRE_REGION": "EU"},
    ):
        from app.config import Settings

        s = Settings()
        assert s.api_url == APIUrl.EU


def test_api_url_default_us() -> None:
    with patch.dict(
        "os.environ",
        {"LIBRE_EMAIL": "a@b.com", "LIBRE_PASSWORD": "pw"},
        clear=False,
    ):
        from app.config import Settings

        s = Settings()
        assert s.api_url == APIUrl.US
