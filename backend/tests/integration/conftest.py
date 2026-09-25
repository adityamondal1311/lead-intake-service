from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import models  # noqa: F401  (registers every table, so clean_tables truncates all of them)
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from tests.integration.webhook_support import SECRET, VERIFY_TOKEN


def _alembic_config() -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Build the schema with the real migrations (not create_all), so every test run also
    proves the migrations apply cleanly."""
    command.upgrade(_alembic_config(), "head")


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    """Empty every table after each test so tests never depend on each other's data."""
    yield
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    if tables:
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def alembic_config() -> Config:
    return _alembic_config()


@pytest.fixture
def db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def webhook_settings() -> Iterator[None]:
    """Fixed webhook secrets, so a developer's backend/.env can never change what tests see."""

    app.dependency_overrides[get_settings] = lambda: Settings(
        meta_app_secret=SECRET, meta_verify_token=VERIFY_TOKEN
    )
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
