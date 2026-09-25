"""Send a signed, Meta-style lead webhook to the service (for local testing and demos).

The signature is computed here independently of the app code (stdlib hmac), exactly as Meta
does: HMAC-SHA256 over the raw body bytes, keyed with the app secret, sent as
X-Hub-Signature-256: sha256=<hex>.

Examples (from backend/):
    uv run python scripts/send_test_webhook.py --secret my-app-secret
    uv run python scripts/send_test_webhook.py --lead-id meta_lead_42 --phone "+919812345678"
    uv run python scripts/send_test_webhook.py --event-id evt_1 --event-id evt_1  # sent twice
    uv run python scripts/send_test_webhook.py --bad-signature                     # expect 401
    uv run python scripts/send_test_webhook.py --url https://<backend>/webhook/meta-lead

The secret defaults to the META_APP_SECRET environment variable.
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime

DEFAULT_URL = "http://localhost:8000/webhook/meta-lead"


def build_payload(args: argparse.Namespace, event_id: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "event_id": event_id,
        "lead_id": args.lead_id,
        "created_time": datetime.now(UTC).isoformat(timespec="seconds"),
        "campaign_id": args.campaign_id,
        "form_id": "form_demo",
        "ad_id": "ad_demo",
        "full_name": args.name,
    }
    if args.email:
        payload["email"] = args.email
    if args.phone:
        payload["phone"] = args.phone
    return payload


def send(url: str, secret: str, payload: dict[str, object], bad_signature: bool) -> int:
    body = json.dumps(payload).encode()
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if bad_signature:
        signature = "sha256=" + "0" * 64
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status, text = response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        status, text = error.code, error.read().decode()
    print(f"{payload['event_id']} -> HTTP {status} {text}")
    return status


def main() -> int:
    suffix = uuid.uuid4().hex[:8]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--secret", default=os.environ.get("META_APP_SECRET", ""))
    parser.add_argument(
        "--event-id",
        action="append",
        help="Repeat to send several deliveries (default: one new random id)",
    )
    parser.add_argument("--lead-id", default=f"meta_lead_{suffix}")
    parser.add_argument("--name", default="Rahul Sharma")
    parser.add_argument("--email", default=f"rahul.{suffix}@example.com")
    parser.add_argument("--phone", default="+919999999999")
    parser.add_argument("--campaign-id", default="cmp_demo")
    parser.add_argument("--bad-signature", action="store_true", help="Send a wrong signature")
    args = parser.parse_args()

    if not args.secret:
        parser.error("no secret: pass --secret or set META_APP_SECRET")

    statuses = [
        send(args.url, args.secret, build_payload(args, event_id), args.bad_signature)
        for event_id in (args.event_id or [f"evt_{suffix}"])
    ]
    return 0 if all(200 <= status < 300 for status in statuses) else 1


if __name__ == "__main__":
    sys.exit(main())
