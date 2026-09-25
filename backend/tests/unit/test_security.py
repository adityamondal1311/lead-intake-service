import hashlib
import hmac

import pytest

from app.core.security import compute_signature, is_valid_signature, is_valid_verify_token

SECRET = "app-secret"
BODY = b'{"event_id":"evt_1","lead_id":"L1","full_name":"A","email":"a@example.com"}'


def test_signature_matches_an_independent_hmac_sha256_of_the_raw_body() -> None:
    expected = "sha256=" + hmac.new(SECRET.encode(), BODY, hashlib.sha256).hexdigest()

    assert compute_signature(SECRET, BODY) == expected


def test_valid_signature_is_accepted() -> None:
    assert is_valid_signature(SECRET, BODY, compute_signature(SECRET, BODY))


@pytest.mark.parametrize(
    ("secret", "body", "header"),
    [
        pytest.param(SECRET, BODY + b" ", compute_signature(SECRET, BODY), id="tampered-body"),
        pytest.param(SECRET, BODY, compute_signature("other-secret", BODY), id="wrong-secret"),
        pytest.param(SECRET, BODY, None, id="missing-header"),
        pytest.param(SECRET, BODY, "", id="empty-header"),
        pytest.param(
            SECRET,
            BODY,
            compute_signature(SECRET, BODY).removeprefix("sha256="),
            id="missing-prefix",
        ),
        pytest.param(SECRET, BODY, "sha256=é", id="non-ascii-header"),
        # Anyone can compute an HMAC with an empty key, so an unconfigured secret must never pass.
        pytest.param("", BODY, compute_signature("", BODY), id="empty-secret"),
    ],
)
def test_invalid_signatures_are_rejected(secret: str, body: bytes, header: str | None) -> None:
    assert not is_valid_signature(secret, body, header)


@pytest.mark.parametrize(
    ("expected", "provided", "valid"),
    [
        ("token", "token", True),
        ("token", "wrong", False),
        ("token", None, False),
        ("", "", False),  # unconfigured token never validates
    ],
)
def test_verify_token(expected: str, provided: str | None, valid: bool) -> None:
    assert is_valid_verify_token(expected, provided) is valid
