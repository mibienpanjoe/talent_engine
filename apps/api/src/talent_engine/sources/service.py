from sqlalchemy.dialects.postgresql import insert
from talent_engine.campaigns.lifecycle import now

from .repository import excerpts, run_evidence, run_sources, sources


def persist(db, claim, output):
    """Called after worker fencing, or inside a new private fixture transaction."""
    source_ids, excerpt_ids = [], []
    for record in output["sources"]:
        fields = {k: v for k, v in record.items() if k != "excerpts"}
        db.execute(
            insert(sources)
            .values(**fields, application_id=claim.application_id, created_at=now(db))
            .on_conflict_do_nothing()
        )
        source_ids.append(record["id"])
        db.execute(
            insert(run_sources)
            .values(
                run_id=claim.run_id,
                source_version_id=record["id"],
                application_id=claim.application_id,
            )
            .on_conflict_do_nothing()
        )
        for excerpt in record["excerpts"]:
            db.execute(
                insert(excerpts)
                .values(**excerpt, application_id=claim.application_id)
                .on_conflict_do_nothing()
            )
            db.execute(
                insert(run_evidence)
                .values(
                    run_id=claim.run_id,
                    excerpt_id=excerpt["id"],
                    application_id=claim.application_id,
                )
                .on_conflict_do_nothing()
            )
            excerpt_ids.append(excerpt["id"])
    return dict(
        version=output["version"],
        snapshot_id=output["snapshot_id"],
        source_ids=source_ids,
        evidence_ids=excerpt_ids,
    )
