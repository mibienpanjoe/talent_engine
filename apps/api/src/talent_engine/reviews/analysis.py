from uuid import uuid4

from sqlalchemy import select
from talent_engine.applications.data import analysis_runs, applications, jobs
from talent_engine.campaigns.lifecycle import now
from talent_engine.errors import AccessError
from talent_engine.sources.data import run_sources, sources

from .service import bump


def failed_source(source):
    meta = source["extraction_metadata"]
    return (
        source["state"] != "available"
        or bool(source["error_code"])
        or any(
            x["status"] == "failed"
            for x in meta.get("web", [])
            + meta.get("ocr", [])
            + ((meta.get("github") or {}).get("files", []))
        )
    )


def request_analysis(db, row, payload):
    if db.scalar(
        select(jobs.c.id).where(
            jobs.c.application_id == row["id"],
            jobs.c.state.in_(["queued", "running", "waiting"]),
        )
    ):
        raise AccessError(409, "analysis_active", "One analysis is already active")
    base = (
        db.execute(
            select(analysis_runs).where(
                analysis_runs.c.id == payload.base_run_id,
                analysis_runs.c.application_id == row["id"],
            )
        )
        .mappings()
        .first()
    )
    if not base or base["state"] not in {"completed", "completed_partial", "failed"}:
        raise AccessError(
            422,
            "invalid_analysis_base",
            "Select a terminal analysis of this application",
        )
    records = (
        db.execute(
            select(sources)
            .join(run_sources, run_sources.c.source_version_id == sources.c.id)
            .where(
                run_sources.c.run_id == base["id"],
                sources.c.application_id == row["id"],
            )
        )
        .mappings()
        .all()
    )
    by_id = {r["id"]: r for r in records}
    if (
        any(ident not in by_id for ident in payload.source_ids)
        or payload.reason == "retry_sources"
        and any(not failed_source(by_id[ident]) for ident in payload.source_ids)
    ):
        raise AccessError(
            422, "invalid_retry_source", "Select failed sources of the requested base"
        )
    ident = uuid4()
    timestamp = now(db)
    db.execute(
        analysis_runs.insert().values(
            id=ident,
            application_id=row["id"],
            snapshot_id=row["snapshot_id"],
            reason=payload.reason,
            state="queued",
            created_at=timestamp,
        )
    )
    db.execute(
        jobs.insert().values(
            id=uuid4(),
            run_id=ident,
            application_id=row["id"],
            state="queued",
            lease_generation=0,
            application_generation=row["processing_generation"],
            created_at=timestamp,
        )
    )
    # Validated answers remain immutable; checkpoints still enter through fencing.
    bump(
        db,
        row,
        processing_state="queued",
        processing_revision=applications.c.processing_revision + 1,
    )
    return ident


def request_for_run(db, run_id):
    from .repository import application_actions

    return db.scalar(
        select(application_actions.c.request).where(
            application_actions.c.result_id == run_id,
            application_actions.c.route == "analyses",
        )
    )


def reused_sources(db, application_id, request):
    selected = set(request["source_ids"])
    records = (
        db.execute(
            select(sources)
            .join(run_sources, run_sources.c.source_version_id == sources.c.id)
            .where(
                run_sources.c.run_id == request["base_run_id"],
                sources.c.application_id == application_id,
            )
        )
        .mappings()
        .all()
    )
    from talent_engine.sources.data import excerpts

    result = []
    target_keys = set()
    for source in records:
        if str(source["id"]) in selected:
            target_keys.add(source["source_key"])
            continue
        fields = {
            k: v for k, v in source.items() if k not in {"application_id", "created_at"}
        }
        for key in ("id", "upload_id"):
            if fields[key] is not None:
                fields[key] = str(fields[key])
        fields["excerpts"] = [
            {
                k: str(v) if k in {"id", "source_version_id"} else v
                for k, v in e.items()
                if k != "application_id"
            }
            for e in db.execute(
                select(excerpts).where(
                    excerpts.c.source_version_id == source["id"],
                    excerpts.c.application_id == application_id,
                )
            ).mappings()
        ]
        result.append(fields)
    # No previous manifest means the whole collection step failed before checkpoint.
    return result, target_keys if records else None
