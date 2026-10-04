"""Signed pagination bound to owner, revision, view and active filters."""

import base64
import hashlib
import hmac
import json

from talent_engine.errors import AccessError


def encode(settings, owner_id, campaign, position, *, scope=None):
    data = json.dumps(
        [
            str(owner_id),
            str(campaign["id"]),
            str(campaign["list_revision"]),
            scope or ["all", None, None],
            position,
        ],
        separators=(",", ":"),
    ).encode()
    body = base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    signature = hmac.new(
        settings.csrf_secret.get_secret_value().encode(),
        ("applications-cursor-v2:" + body).encode(),
        hashlib.sha256,
    ).hexdigest()
    return body + "." + signature


def decode(settings, owner_id, campaign, cursor, *, scope=None):
    try:
        body, signature = cursor.split(".")
        expected = hmac.new(
            settings.csrf_secret.get_secret_value().encode(),
            ("applications-cursor-v2:" + body).encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if (
            len(data) != 5
            or data[:2] != [str(owner_id), str(campaign["id"])]
            or data[3] != (scope or ["all", None, None])
            or type(data[4]) is not int
            or not 0 <= data[4] <= 1000000
        ):
            raise ValueError("Invalid binding")
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise AccessError(
            400, "invalid_cursor", "Cursor is not valid for this list"
        ) from None
    if data[2] != str(campaign["list_revision"]):
        raise AccessError(
            409, "cursor_invalidated", "Applications changed; reload the list"
        )
    return data[4]
