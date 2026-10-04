"""Persistent source and evaluation steps, finalized under worker fencing."""

from pathlib import Path

from sqlalchemy import select
from talent_engine.applications.data import applications
from talent_engine.applications.schemas import SubmissionInput
from talent_engine.applications.validation import validate_answers
from talent_engine.campaigns.data import snapshots
from talent_engine.documents.data import uploads
from talent_engine.evaluations.service import evaluate
from talent_engine.integrations.llm import ProviderFailure
from talent_engine.integrations.public_web import WebFailure
from talent_engine.sources.extraction import collect_sources


class StepFailure(Exception):
    def __init__(self, code, *, retryable=False, retry_after=None):
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(code)


def process(
    engine,
    claim,
    *,
    upload_directory=None,
    gateway=None,
    ocr_gateway=None,
    portfolio_web=None,
    github_web=None,
    embedder=None,
):
    if claim.step == "evaluate":
        try:
            return evaluate(engine, claim, gateway=gateway, embedder=embedder)
        except ProviderFailure as error:
            raise StepFailure(
                error.code, retryable=error.retryable, retry_after=error.retry_after
            ) from None
        except ValueError:
            raise StepFailure("assessment_invalid") from None
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
            from talent_engine.reviews.analysis import request_for_run, reused_sources

            request = request_for_run(db, claim.run_id)
            reused, only_keys = (
                reused_sources(db, app["id"], request) if request else ([], None)
            )
            app_id, answers = app["id"], app["answers"]
            snapshot_id = str(app["snapshot_id"])
        else:
            raise StepFailure("evaluation_unavailable")
    # Extraction happens after releasing the database connection.
    try:
        sources = collect_sources(
            app_id,
            answers,
            documents,
            upload_directory or Path("/tmp/talent-engine-uploads"),
            ocr_gateway=ocr_gateway,
            retry_errors=claim.attempt < 3,
            portfolio_web=portfolio_web,
            github_web=github_web,
            only_keys=only_keys,
        )
    except (ProviderFailure, WebFailure) as error:
        raise StepFailure(
            error.code, retryable=error.retryable, retry_after=error.retry_after
        ) from None
    return dict(
        version="received-sources-v3", snapshot_id=snapshot_id, sources=reused + sources
    )
