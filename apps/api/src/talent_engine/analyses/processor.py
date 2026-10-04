"""Receive-stage checkpoints. Evaluation adapters arrive in the next phase."""

from sqlalchemy import select
from talent_engine.applications.data import applications
from talent_engine.applications.schemas import SubmissionInput
from talent_engine.applications.validation import validate_answers
from talent_engine.campaigns.data import snapshots
from talent_engine.documents.data import uploads


class StepFailure(Exception):
    def __init__(self, code, *, retryable=False, retry_after=None):
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(code)


def process(engine, claim):
    with engine.connect() as db:
        app = (
            db.execute(
                select(applications)
                .where(applications.c.id == claim.application_id)
                .where(applications.c.deleted_at.is_(None))
            )
            .mappings()
            .first()
        )
        if not app:
            raise StepFailure("application_unavailable")
        snapshot = (
            db.execute(select(snapshots).where(snapshots.c.id == app["snapshot_id"]))
            .mappings()
            .one()
        )
        if claim.step == "extract_answers":
            payload = SubmissionInput(
                snapshot_id=app["snapshot_id"],
                contact=app["contact"],
                answers=app["answers"],
            )
            validate_answers(payload, snapshot["configuration"])
            return {
                "version": "answers-v1",
                "snapshot_id": str(app["snapshot_id"]),
                "answers": [a.model_dump(mode="json") for a in payload.answers],
            }
        if claim.step == "source_manifest":
            documents = (
                db.execute(
                    select(uploads)
                    .where(uploads.c.application_id == app["id"])
                    .order_by(uploads.c.id)
                )
                .mappings()
                .all()
            )
            return {
                "version": "received-sources-v1",
                "snapshot_id": str(app["snapshot_id"]),
                "documents": [
                    {
                        k: str(row[k]) if k in {"id", "question_id"} else row[k]
                        for k in ("id", "question_id", "sha256", "bytes", "media_type")
                    }
                    for row in documents
                ],
                "links": [
                    {"question_id": a["question_id"], "url": a["value"]}
                    for a in app["answers"]
                    if a["kind"] == "url"
                ],
            }
    # This phase never fabricates an evaluation or a successful analysis.
    raise StepFailure("evaluation_unavailable")
