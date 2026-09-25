"""Meta webhook authenticity checks.

Meta signs every webhook delivery with HMAC-SHA256 over the raw request body, keyed with the app
secret, and sends it as `X-Hub-Signature-256: sha256=<hex digest>`. Recomputing that digest
proves the request came from someone holding the secret and that the body was not modified.
"""

import hashlib
import hmac

SIGNATURE_HEADER = "X-Hub-Signature-256"
_SIGNATURE_PREFIX = "sha256="


def compute_signature(secret: str, body: bytes) -> str:
    """The X-Hub-Signature-256 header value Meta would send for this body."""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"{_SIGNATURE_PREFIX}{digest}"


def _constant_time_equal(a: str, b: str) -> bool:
    # compare_digest takes the same time wherever the first difference is, so response timing
    # cannot be used to guess a valid signature or token byte by byte.
    return hmac.compare_digest(a.encode(), b.encode())


def is_valid_signature(secret: str, body: bytes, header_value: str | None) -> bool:
    """True only if the header is the HMAC of exactly these bytes under a configured secret.

    An empty secret never validates: anyone can compute an HMAC with an empty key.
    """
    if not secret or not header_value:
        return False
    return _constant_time_equal(header_value, compute_signature(secret, body))


def is_valid_verify_token(expected: str, provided: str | None) -> bool:
    """Checks the hub.verify_token Meta sends when a webhook subscription is set up."""
    if not expected or not provided:
        return False
    return _constant_time_equal(provided, expected)
