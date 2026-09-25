from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app


def test_health_reports_database_ok_against_real_postgres(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable(client: TestClient) -> None:
    # A real connection failure (nothing listens on port 1), not a mocked exception.
    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
        connect_args={"connect_timeout": 1},
    )

    def unreachable_db() -> Iterator[Session]:
        with Session(unreachable) as session:
            yield session

    app.dependency_overrides[get_db] = unreachable_db

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "error"}


def test_generates_request_id_when_caller_sends_none(client: TestClient) -> None:
    response = client.get("/health")

    assert len(response.headers["X-Request-ID"]) == 32


def test_echoes_well_formed_caller_request_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "trace-abc.123"})

    assert response.headers["X-Request-ID"] == "trace-abc.123"


def test_replaces_malformed_request_id_to_protect_logs(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": 'evil" injected {json}'})

    assert response.headers["X-Request-ID"] != 'evil" injected {json}'
    assert len(response.headers["X-Request-ID"]) == 32
