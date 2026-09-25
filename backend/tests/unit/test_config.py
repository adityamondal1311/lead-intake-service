import pytest

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
