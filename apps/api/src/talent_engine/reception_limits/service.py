import hashlib
import hmac
import math
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert
from talent_engine.campaigns.lifecycle import now
from talent_engine.errors import AccessError

from .repository import public_limits, transfers


def requests(engine, settings, scopes):
    keys = sorted(
        (
            hmac.new(
                settings.csrf_secret.get_secret_value().encode(),
                f"public-limit-v1:{scope}".encode(),
                hashlib.sha256,
            ).hexdigest(),
            maximum,
        )
        for scope, maximum in scopes
    )
    blocked = 0
    with engine.begin() as db:
        timestamp = now(db)
        for key, maximum in keys:
            expired = public_limits.c.expires_at <= timestamp
            row = (
                db.execute(
                    insert(public_limits)
                    .values(
                        key=key, requests=1, expires_at=timestamp + timedelta(minutes=1)
                    )
                    .on_conflict_do_update(
                        index_elements=[public_limits.c.key],
                        set_={
                            "requests": case(
                                (expired, 1),
                                else_=func.least(
                                    public_limits.c.requests + 1, maximum + 1
                                ),
                            ),
                            "expires_at": case(
                                (expired, timestamp + timedelta(minutes=1)),
                                else_=public_limits.c.expires_at,
                            ),
                        },
                    )
                    .returning(public_limits)
                )
                .mappings()
                .one()
            )
            if row["requests"] > maximum:
                blocked = max(
                    blocked, math.ceil((row["expires_at"] - timestamp).total_seconds())
                )
    if blocked:
        raise AccessError(
            429, "rate_limited", "Too many requests; retry later", max(1, blocked)
        )


def reserve_transfer(db, session_id, storage_key=None):
    # Caller holds the upload-session lock, shared by every API instance.
    timestamp = now(db)
    db.execute(
        transfers.delete().where(
            (transfers.c.session_id == session_id)
            & (transfers.c.expires_at <= timestamp)
        )
    )
    active = (
        db.execute(select(transfers).where(transfers.c.session_id == session_id))
        .mappings()
        .all()
    )
    if len(active) >= 2:
        retry = min(
            math.ceil((r["expires_at"] - timestamp).total_seconds()) for r in active
        )
        raise AccessError(
            429,
            "rate_limited",
            "Two document transfers are already active",
            max(1, retry),
        )
    transfer_id = uuid4()
    db.execute(
        transfers.insert().values(
            id=transfer_id,
            session_id=session_id,
            storage_key=storage_key,
            expires_at=timestamp + timedelta(seconds=120),
        )
    )
    return transfer_id
