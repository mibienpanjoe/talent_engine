import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import unicodedata
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from talent_engine.campaigns.data import snapshots
from talent_engine.campaigns.lifecycle import active_snapshot, now
from talent_engine.campaigns.schemas import DraftConfiguration
from talent_engine.errors import AccessError

from .repository import upload_sessions, uploads
from .schemas import UploadSessionCreated


def token_hash(settings, token):
    return hmac.new(
        settings.csrf_secret.get_secret_value().encode(),
        ("upload-v1:" + token).encode(),
        hashlib.sha256,
    ).hexdigest()


def storage_path(settings, key):
    parts = key.split("/")
    if (
        len(parts) != 2
        or parts[0] not in {"real", "test"}
        or str(UUID(parts[1])) != parts[1]
    ):
        raise ValueError("Invalid private storage key")
    return settings.upload_directory / parts[0] / parts[1]


def snapshot_for_upload(db, campaign, snapshot_id, mode):
    if mode == "real":
        snapshot = active_snapshot(db, campaign)
        if snapshot["id"] != snapshot_id:
            raise AccessError(409, "snapshot_conflict", "Form changed")
        config = DraftConfiguration.model_validate(snapshot["configuration"])
        if campaign["state"] != "published" or (
            config.deadline and now(db) >= config.deadline
        ):
            raise AccessError(409, "campaign_closed", "Campaign closed")
    else:
        snapshot = (
            db.execute(
                select(snapshots).where(
                    (snapshots.c.id == snapshot_id)
                    & (snapshots.c.campaign_id == campaign["id"])
                    & (snapshots.c.mode == "test")
                )
            )
            .mappings()
            .first()
        )
        if not snapshot:
            raise AccessError(404, "not_found", "Snapshot unavailable")
    return snapshot


def prepare_session(db, settings, campaign, snapshot_id, mode, owner_id=None):
    snapshot_for_upload(db, campaign, snapshot_id, mode)
    token = secrets.token_urlsafe(32)
    row = dict(
        id=uuid4(),
        campaign_id=campaign["id"],
        snapshot_id=snapshot_id,
        mode=mode,
        owner_id=owner_id,
        token_hash=token_hash(settings, token),
        expires_at=now(db) + timedelta(hours=24),
    )
    db.execute(upload_sessions.insert().values(**row))
    return UploadSessionCreated(
        id=row["id"],
        snapshot_id=snapshot_id,
        upload_token=token,
        expires_at=row["expires_at"],
    )


def authorized_session(db, settings, session_id, token, mode, owner_id=None, lock=True):
    query = select(upload_sessions).where(upload_sessions.c.id == session_id)
    if lock:
        query = query.with_for_update()
    row = db.execute(query).mappings().first()
    if (
        not row
        or not token
        or len(token) > 200
        or not hmac.compare_digest(row["token_hash"], token_hash(settings, token))
        or row["mode"] != mode
        or (mode == "test" and row["owner_id"] != owner_id)
    ):
        raise AccessError(404, "not_found", "Upload session unavailable")
    if row["expires_at"] <= now(db):
        raise AccessError(410, "upload_expired", "Upload session expired")
    return row


def clean_filename(name):
    name = "".join(
        c for c in (name or "document") if not unicodedata.category(c).startswith("C")
    )
    name = name.replace("\\", "/").split("/")[-1].strip(" .")[:200]
    return name or "document"


def detect_file(path):
    try:
        result = subprocess.run(
            [sys.executable, "-m", "talent_engine.documents.inspect_file", str(path)],
            timeout=60,
            capture_output=True,
            env={"PATH": os.defpath},
            check=True,
        )
        return json.loads(result.stdout)["media_type"]
    except (subprocess.SubprocessError, ValueError, KeyError):
        raise AccessError(
            415, "unsupported_file_type", "Use a readable PDF, PNG or JPEG"
        ) from None


def validate_uploads(
    db, settings, campaign, snapshot, payload, *, replay_original=None
):
    originals = replay_original or {}
    selected = [
        (a, uid) for a in payload.answers if a.kind == "file" for uid in a.value
    ]
    if not selected:
        return {}, []
    if len(selected) > 5 or len({uid for _, uid in selected}) != len(selected):
        raise AccessError(422, "invalid_upload", "At most five distinct documents")
    original_ids = {item["id"]: item for items in originals.values() for item in items}
    session = None
    manifest = {}
    rows = []
    total = 0
    for answer, uid in selected:
        original = original_ids.get(str(uid))
        if original and original["question_id"] == str(answer.question_id):
            item = original
        else:
            if not session:
                session = authorized_session(
                    db,
                    settings,
                    payload.upload_session_id,
                    payload.upload_token,
                    snapshot["mode"],
                    campaign["owner_id"],
                )
                if (
                    session["campaign_id"] != campaign["id"]
                    or session["snapshot_id"] != snapshot["id"]
                ):
                    raise AccessError(
                        422, "invalid_upload", "Upload belongs to another form"
                    )
            row = (
                db.execute(select(uploads).where(uploads.c.id == uid).with_for_update())
                .mappings()
                .first()
            )
            if (
                not row
                or row["session_id"] != session["id"]
                or row["question_id"] != answer.question_id
            ):
                raise AccessError(
                    422,
                    "invalid_upload",
                    "Document belongs to another session or question",
                )
            if row["expires_at"] <= now(db):
                raise AccessError(410, "upload_expired", "Document expired")
            if row["state"] != "ready" or row["application_id"]:
                raise AccessError(422, "invalid_upload", "Document is not available")
            item = {
                k: str(row[k]) if k in {"id", "question_id"} else row[k]
                for k in (
                    "id",
                    "question_id",
                    "filename",
                    "media_type",
                    "bytes",
                    "sha256",
                )
            }
            rows.append(row)
        manifest.setdefault(str(answer.question_id), []).append(item)
        total += item["bytes"]
    if total > 31457280:
        raise AccessError(413, "payload_too_large", "Documents exceed 30 MiB")
    return manifest, rows


def attach_files(db, settings, campaign, snapshot, payload, app_id):
    manifest, rows = validate_uploads(db, settings, campaign, snapshot, payload)
    for row in rows:
        db.execute(
            uploads.update()
            .where(uploads.c.id == row["id"])
            .values(application_id=app_id)
        )
    return manifest
