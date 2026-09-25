from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app


class _StubSession:
    def execute(self, *_args: object) -> None:
        return None


def test_health_returns_ok_when_database_responds() -> None:
    app.dependency_overrides[get_db] = lambda: _StubSession()
    try:
        response = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
