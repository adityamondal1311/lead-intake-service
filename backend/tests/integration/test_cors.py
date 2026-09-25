"""The browser flow the dashboard depends on: allowed origin, blocked origin, PATCH preflight,
and a readable X-Request-ID, including on error responses."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from httpx import Headers

from app.core.config import Settings
from app.main import create_app
from app.services import lead_service

DASHBOARD = "https://dashboard.example.com"
OTHER = "https://evil.example.com"


@pytest.fixture
def cors_client() -> Iterator[TestClient]:
    # Explicit settings, so a developer's backend/.env cannot change the allowed origins.
    with TestClient(create_app(Settings(cors_origins=[DASHBOARD]))) as client:
        yield client


def _exposed_headers(response_headers: Headers) -> set[str]:
    raw = response_headers.get("access-control-expose-headers", "")
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def test_allowed_origin_gets_cors_headers_and_can_read_the_request_id(
    cors_client: TestClient,
) -> None:
    response = cors_client.get("/leads", headers={"Origin": DASHBOARD})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DASHBOARD
    assert "x-request-id" in _exposed_headers(response.headers)
    assert response.headers["x-request-id"]


def test_other_origin_gets_no_cors_headers(cors_client: TestClient) -> None:
    response = cors_client.get("/leads", headers={"Origin": OTHER})

    # The server still answers (CORS is enforced by the browser), but without the headers the
    # browser will not let the other site's JavaScript read the response.
    assert "access-control-allow-origin" not in response.headers


def test_patch_preflight_from_the_dashboard_is_allowed(cors_client: TestClient) -> None:
    response = cors_client.options(
        f"/leads/{uuid.uuid4()}/status",
        headers={
            "Origin": DASHBOARD,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DASHBOARD
    assert "PATCH" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_preflight_from_another_origin_is_refused(cors_client: TestClient) -> None:
    response = cors_client.options(
        "/leads/x/status",
        headers={"Origin": OTHER, "Access-Control-Request-Method": "PATCH"},
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_a_method_the_dashboard_never_uses_is_refused(
    cors_client: TestClient,
) -> None:
    response = cors_client.options(
        "/leads",
        headers={"Origin": DASHBOARD, "Access-Control-Request-Method": "DELETE"},
    )

    # Starlette still echoes the (allowed) origin, but the browser refuses the request because
    # DELETE is not among the allowed methods.
    assert response.status_code == 400
    assert "DELETE" not in response.headers["access-control-allow-methods"]


def test_error_responses_still_carry_cors_headers(
    cors_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without CORS headers on a 404/500, the browser hides the error body and the dashboard
    cannot show the message or request id."""
    not_found = cors_client.get(f"/leads/{uuid.uuid4()}", headers={"Origin": DASHBOARD})

    def fail(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(lead_service, "list_leads", fail)
    crashed = cors_client.get("/leads", headers={"Origin": DASHBOARD})

    for response, status in ((not_found, 404), (crashed, 500)):
        assert response.status_code == status
        assert response.headers["access-control-allow-origin"] == DASHBOARD
        assert "x-request-id" in _exposed_headers(response.headers)
        assert response.json()["error"]["requestId"] == response.headers["x-request-id"]
