from app.core.config import get_settings


def test_settings_loads_secret_key():
    settings = get_settings()
    assert settings.secret_key, "SECRET_KEY should be configurable"


