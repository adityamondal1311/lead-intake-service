import pytest
from pydantic import ValidationError
from pydantic_settings.exceptions import SettingsError

from app.core.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Railway / Heroku style URLs get the psycopg 3 driver pinned.
        ("postgres://u:p@db:5432/app", "postgresql+psycopg://u:p@db:5432/app"),
        ("postgresql://u:p@db:5432/app", "postgresql+psycopg://u:p@db:5432/app"),
        # Already explicit: left untouched.
        ("postgresql+psycopg://u:p@db:5432/app", "postgresql+psycopg://u:p@db:5432/app"),
    ],
)
def test_database_url_is_normalized_to_psycopg_driver(given: str, expected: str) -> None:
    assert Settings(database_url=given).database_url == expected


@pytest.mark.parametrize(
    ("secret", "token", "missing"),
    [
        ("", "", "META_APP_SECRET, META_VERIFY_TOKEN"),
        ("", "token", "META_APP_SECRET"),
        ("secret", "", "META_VERIFY_TOKEN"),
    ],
)
def test_production_refuses_to_start_without_webhook_secrets(
    secret: str, token: str, missing: str
) -> None:
    with pytest.raises(ValueError, match=f"{missing} must be set when ENVIRONMENT=production"):
        Settings(environment="production", meta_app_secret=secret, meta_verify_token=token)


def test_production_starts_with_webhook_secrets_and_local_allows_them_empty() -> None:
    Settings(environment="production", meta_app_secret="secret", meta_verify_token="token")
    Settings(environment="local", meta_app_secret="", meta_verify_token="")


@pytest.mark.parametrize("value", ["prod", "Production", "PROD", "staging", "abc", ""])
def test_unknown_environment_is_rejected(value: str) -> None:
    # A typo must not start the app with the production checks silently skipped.
    with pytest.raises(ValidationError, match="environment"):
        Settings(environment=value)


@pytest.mark.parametrize("value", ["local", "test"])
def test_known_non_production_environments_are_accepted(value: str) -> None:
    assert Settings(environment=value).environment == value


@pytest.mark.parametrize("value", ["info", "VERBOSE", "TRACE", ""])
def test_unknown_log_level_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="log_level"):
        Settings(log_level=value)


@pytest.mark.parametrize("value", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_standard_log_levels_are_accepted(value: str) -> None:
    assert Settings(log_level=value).log_level == value


def test_cors_origins_are_read_as_a_json_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", '["https://app.example.com", "http://localhost:5173"]')

    assert Settings().cors_origins == ["https://app.example.com", "http://localhost:5173"]


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("https://app.example.com", id="bare-string-not-json"),
        pytest.param("https://a.example.com,https://b.example.com", id="comma-separated"),
        pytest.param('["https://app.example.com"', id="broken-json"),
    ],
)
def test_malformed_cors_origins_env_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("CORS_ORIGINS", value)

    with pytest.raises(SettingsError, match="cors_origins"):
        Settings()


@pytest.mark.parametrize(
    "origin",
    [
        pytest.param("https://app.example.com/", id="trailing-slash"),
        pytest.param("https://app.example.com/dashboard", id="path"),
        pytest.param("app.example.com", id="no-scheme"),
        pytest.param("*", id="wildcard"),
    ],
)
def test_origins_that_can_never_match_a_browser_origin_are_rejected(origin: str) -> None:
    with pytest.raises(ValidationError, match="invalid origin"):
        Settings(cors_origins=[origin])
