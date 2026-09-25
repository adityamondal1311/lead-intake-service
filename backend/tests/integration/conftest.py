from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Build the schema with the real migrations (not create_all), so every test run also
    proves the migrations apply cleanly."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    """Empty every table after each test so tests never depend on each other's data."""
    yield
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if tables:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
