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
