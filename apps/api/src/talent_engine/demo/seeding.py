import hashlib
import json
import os
import re
from uuid import uuid4, uuid5

from sqlalchemy import select, text

from talent_engine.access import reviewers
from talent_engine.applications.data import applications, receipts
from talent_engine.applications.schemas import SubmissionInput
from talent_engine.applications.service import receive
from talent_engine.campaigns.data import campaigns, insert_campaign, owned
from talent_engine.campaigns.lifecycle import active_snapshot, create_snapshot, now
from talent_engine.documents.data import uploads
from talent_engine.documents.service import detect_file, prepare_session, storage_path

from .configuration import configuration
from .preloaded import initialize


def stage_documents(db, settings, campaign, snapshot, paths, qid):
    session = prepare_session(db, settings, campaign, snapshot["id"], "real")
    identifiers = []
    for source in paths:
        content = source.read_bytes()
        key = "real/" + str(uuid4())
        path = storage_path(settings, key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open("xb") as stream:
            os.chmod(path, 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        media = detect_file(path)
        ident = uuid4()
        db.execute(
            uploads.insert().values(
                id=ident,
                session_id=session.id,
                question_id=qid,
                filename=source.name,
                media_type=media,
                bytes=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_key=key,
                state="ready",
                created_at=now(db),
                expires_at=session.expires_at,
            )
        )
        identifiers.append(str(ident))
    return session, identifiers


def seed(
    engine, settings, *, login, mode, batch, fixture_root, portfolio=None, github=None
):
    if mode not in {"preloaded", "live"} or not re.fullmatch(
        r"[a-zA-Z0-9_.-]{1,64}", batch
    ):
        raise ValueError("Choose a supported mode and a short batch identifier")
    if mode == "preloaded" and (portfolio or github):
        raise ValueError("External references belong to live mode")
    fixture = json.loads((fixture_root / "demonstrations" / "cases.json").read_text())
    results = []
    with engine.begin() as db:
        db.execute(text("SELECT pg_advisory_xact_lock(527412032)"))
        owner = db.scalar(
            select(reviewers.c.id).where(
                reviewers.c.login == login, reviewers.c.disabled_at.is_(None)
            )
        )
        if owner is None:
            raise ValueError("Initialize the reviewer before seeding demonstrations")
        for domain in fixture["domains"]:
            cid = uuid5(
                owner, f"demo:{fixture['version']}:{mode}:{batch}:{domain['key']}"
            )
            current = (
                db.execute(select(campaigns).where(campaigns.c.id == cid))
                .mappings()
                .first()
            )
            if current is None:
                config = configuration(domain, cid, mode)
                insert_campaign(db, owner, config, campaign_id=cid)
                current = owned(db, cid, owner, lock=True)
                snapshot = create_snapshot(db, current, config, owner, "real")
                db.execute(
                    campaigns.update()
                    .where(campaigns.c.id == cid)
                    .values(
                        state="published", revision=2, active_snapshot_id=snapshot["id"]
                    )
                )
            current = owned(db, cid, owner, lock=True)
            snapshot = active_snapshot(db, current)
            ids = []
            for candidate in (
                domain["candidates"]
                if mode == "preloaded"
                else domain["candidates"][:1]
            ):
                key = str(uuid5(cid, "candidate:" + candidate["name"]))
                application_id = uuid5(cid, "application:" + candidate["name"])
                receipt_id = uuid5(cid, "receipt:" + candidate["name"])
                existing = db.scalar(
                    select(applications.c.id).where(applications.c.id == application_id)
                )
                if existing:
                    ids.append(str(existing))
                    continue
                receipt = (
                    db.execute(select(receipts).where(receipts.c.id == receipt_id))
                    .mappings()
                    .first()
                )
                if receipt:
                    if not receipt["deleted_at"] and receipt["application_id"]:
                        ids.append(str(receipt["application_id"]))
                    continue
                qids = [q["id"] for q in snapshot["configuration"]["questions"]]
                answers = [
                    dict(question_id=qids[i], kind="long_text", value=value)
                    for i, value in enumerate(candidate["answers"])
                    if value
                ]
                answers.append(
                    dict(
                        question_id=qids[3],
                        kind="date",
                        value=candidate.get("available", "2026-10-05"),
                    )
                )
                session = None
                if mode == "live":
                    documents = [
                        fixture_root / "documents" / name
                        for name in (
                            ["amina-demo.pdf", "amina-scan-demo.pdf"]
                            if domain["key"] == "development"
                            else ["fatou-demo.pdf"]
                        )
                    ]
                    session, files = stage_documents(
                        db, settings, current, snapshot, documents, qids[4]
                    )
                    answers.append(dict(question_id=qids[4], kind="file", value=files))
                    if domain["key"] == "development":
                        for qid, url in zip(qids[5:], [portfolio, github], strict=True):
                            if url:
                                answers.append(
                                    dict(question_id=qid, kind="url", value=url)
                                )
                payload = SubmissionInput(
                    snapshot_id=snapshot["id"],
                    contact=dict(
                        name=candidate["name"] + " · dossier fictif",
                        email=domain["key"]
                        + "."
                        + candidate["name"].encode().hex()
                        + "@example.com",
                    ),
                    answers=answers,
                    upload_session_id=session.id if session else None,
                    upload_token=session.upload_token if session else None,
                )
                result, created = receive(
                    db,
                    settings,
                    current,
                    payload,
                    key,
                    application_id=application_id,
                    receipt_id=receipt_id,
                )
                ident = db.scalar(
                    select(receipts.c.application_id).where(
                        receipts.c.receipt_ref == result.receipt_ref
                    )
                )
                if mode == "preloaded" and created:
                    app = (
                        db.execute(
                            select(applications)
                            .where(applications.c.id == ident)
                            .with_for_update()
                        )
                        .mappings()
                        .one()
                    )
                    initialize(
                        db, app, snapshot, candidate, fixture["version"], settings
                    )
                ids.append(str(ident))
                current = owned(db, cid, owner, lock=True)
            results.append(
                dict(
                    domain=domain["key"],
                    mode=mode,
                    campaign_id=str(cid),
                    application_ids=ids,
                )
            )
    return results
