"""Collect expired unattached uploads under the reception row lock."""

from datetime import timedelta

from sqlalchemy import select
from talent_engine.campaigns.lifecycle import now
from talent_engine.config import Settings
from talent_engine.database import build_engine

from .repository import uploads
from .service import storage_path


def collect(engine, settings):
    removed = 0
    with engine.begin() as db:
        rows = (
            db.execute(
                select(uploads)
                .where(
                    uploads.c.application_id.is_(None)
                    & (uploads.c.expires_at <= now(db))
                )
                .with_for_update(skip_locked=True)
                .limit(100)
            )
            .mappings()
            .all()
        )
        paths = [storage_path(settings, row["storage_key"]) for row in rows]
        for row in rows:
            db.execute(uploads.delete().where(uploads.c.id == row["id"]))
    for path in paths:
        path.unlink(missing_ok=True)
        removed += 1
    with engine.connect() as db:
        threshold = (now(db) - timedelta(hours=24)).timestamp()
        references = set(db.scalars(select(uploads.c.storage_key)))
    for mode in ("real", "test"):
        root = settings.upload_directory / mode
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if (
                path.is_file()
                and path.stat().st_mtime < threshold
                and f"{mode}/{path.name}" not in references
            ):
                path.unlink(missing_ok=True)
                removed += 1
    return removed


if __name__ == "__main__":
    settings = Settings()
    engine = build_engine(settings)
    try:
        print(f"Collected {collect(engine, settings)} private temporary files")
    finally:
        engine.dispose()
