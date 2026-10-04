"""Opaque cursor bound to owner, campaign and the received dataset revision."""

import base64
import hashlib
import hmac
import json
from uuid import UUID

from talent_engine.errors import AccessError


def encode(settings, owner_id, campaign, application_id):
    data = json.dumps(
        [
            str(owner_id),
            str(campaign["id"]),
            campaign["list_revision"],
            str(application_id),
        ],
        separators=(",", ":"),
    ).encode()
    body = base64.urlsafe_b64encode(data).rstrip(b"=").decode()
    signature = hmac.new(
        settings.csrf_secret.get_secret_value().encode(),
        ("applications-cursor-v1:" + body).encode(),
        hashlib.sha256,
    ).hexdigest()
    return body + "." + signature


def decode(settings, owner_id, campaign, cursor):
    try:
        body, signature = cursor.split(".")
        expected = hmac.new(
            settings.csrf_secret.get_secret_value().encode(),
            ("applications-cursor-v1:" + body).encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid signature")
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if len(data) != 4 or data[:2] != [str(owner_id), str(campaign["id"])]:
            raise ValueError("Invalid binding")
        application_id = UUID(data[3])
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise AccessError(
            400, "invalid_cursor", "Cursor is not valid for this list"
        ) from None
    if data[2] != campaign["list_revision"]:
        raise AccessError(
            409, "cursor_invalidated", "Applications changed; reload the list"
        )
    return application_id
