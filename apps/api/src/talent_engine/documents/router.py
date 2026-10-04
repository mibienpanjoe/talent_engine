import asyncio
import hashlib
import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import FileResponse
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from talent_engine.access import build_access_guards
from talent_engine.applications.router import owned_application
from talent_engine.campaigns.lifecycle import now, public_campaign
from talent_engine.campaigns.repository import owned, snapshots
from talent_engine.campaigns.schemas import DraftConfiguration
from talent_engine.errors import AccessError, Error

from .repository import uploads
from .schemas import Upload, UploadSessionCreated, UploadSessionInput
from .service import (
    authorized_session,
    clean_filename,
    detect_file,
    prepare_session,
    snapshot_for_upload,
    storage_path,
)


def build_document_router(engine, settings):
    _, read_guard, write_guard = build_access_guards(engine, settings)
    router = APIRouter(
        prefix="/api/v1",
        tags=["documents"],
        responses={
            code: {"model": Error} for code in [401, 403, 404, 409, 410, 413, 415, 422]
        },
    )

    @router.post(
        "/public/campaigns/{public_token}/upload-sessions",
        response_model=UploadSessionCreated,
        status_code=201,
        operation_id="prepare_uploads",
    )
    def prepare(public_token: str, payload: UploadSessionInput, response: Response):
        with engine.begin() as db:
            campaign = public_campaign(db, public_token, lock=True)
            result = prepare_session(
                db, settings, campaign, payload.snapshot_id, "real"
            )
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.post(
        "/test-snapshots/{snapshot_id}/upload-sessions",
        response_model=UploadSessionCreated,
        status_code=201,
        operation_id="prepare_test_uploads",
    )
    def prepare_test(
        snapshot_id: UUID,
        payload: UploadSessionInput,
        response: Response,
        session=Depends(write_guard),
    ):
        with engine.begin() as db:
            snapshot = (
                db.execute(select(snapshots).where(snapshots.c.id == snapshot_id))
                .mappings()
                .first()
            )
            if (
                not snapshot
                or snapshot["mode"] != "test"
                or payload.snapshot_id != snapshot_id
            ):
                raise AccessError(404, "not_found", "Test snapshot unavailable")
            campaign = owned(
                db, snapshot["campaign_id"], session["reviewer_id"], lock=True
            )
            result = prepare_session(
                db, settings, campaign, snapshot_id, "test", session["reviewer_id"]
            )
        response.headers["Cache-Control"] = "no-store"
        return result

    async def save(request, session_id, token, mode, owner_id=None):
        with engine.connect() as db:
            authorized_session(
                db, settings, session_id, token, mode, owner_id, lock=False
            )
        key = mode + "/" + str(uuid4())
        path = storage_path(settings, key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        persistence_attempted = False
        try:
            async with asyncio.timeout(120):
                async with request.form(
                    max_files=1, max_fields=1, max_part_size=1024
                ) as form:
                    if len(form.multi_items()) != 2 or set(form) != {
                        "question_id",
                        "file",
                    }:
                        raise AccessError(
                            422, "validation_error", "Provide one question and document"
                        )
                    document = form["file"]
                    if not isinstance(document, UploadFile):
                        raise AccessError(422, "validation_error", "Document required")
                    try:
                        question_id = UUID(str(form["question_id"]))
                    except ValueError:
                        raise AccessError(
                            422, "validation_error", "Invalid question"
                        ) from None
                    size = 0
                    digest = hashlib.sha256()
                    with open(path, "xb") as stream:
                        os.chmod(path, 0o600)
                        while chunk := await document.read(65536):
                            size += len(chunk)
                            if size > 10485760:
                                raise AccessError(
                                    413, "payload_too_large", "Document exceeds 10 MiB"
                                )
                            digest.update(chunk)
                            stream.write(chunk)
                        stream.flush()
                        os.fsync(stream.fileno())
                    filename = clean_filename(document.filename)
                    if not size:
                        raise AccessError(
                            415, "unsupported_file_type", "Empty document"
                        )
            media = await run_in_threadpool(detect_file, path)

            def persist():
                with engine.begin() as db:
                    # Same lock order as reception: campaign, session, uploads.
                    preliminary = authorized_session(
                        db, settings, session_id, token, mode, owner_id, lock=False
                    )
                    if mode == "real":
                        from talent_engine.campaigns.repository import campaigns

                        campaign = (
                            db.execute(
                                select(campaigns)
                                .where(campaigns.c.id == preliminary["campaign_id"])
                                .with_for_update()
                            )
                            .mappings()
                            .one()
                        )
                    else:
                        campaign = owned(
                            db, preliminary["campaign_id"], owner_id, lock=True
                        )
                    session = authorized_session(
                        db, settings, session_id, token, mode, owner_id
                    )
                    snapshot = snapshot_for_upload(
                        db, campaign, session["snapshot_id"], mode
                    )
                    q = next(
                        (
                            q
                            for q in DraftConfiguration.model_validate(
                                snapshot["configuration"]
                            ).questions
                            if q.id == question_id and q.type == "file"
                        ),
                        None,
                    )
                    if not q or (
                        q.constraints.allowed_media_types is not None
                        and media not in q.constraints.allowed_media_types
                    ):
                        raise AccessError(
                            422,
                            "invalid_upload",
                            "Document not accepted for this question",
                        )
                    if size > (q.constraints.max_bytes or 10485760):
                        raise AccessError(
                            413, "payload_too_large", "Document exceeds question limit"
                        )
                    current = (
                        db.execute(
                            select(uploads).where(uploads.c.session_id == session_id)
                        )
                        .mappings()
                        .all()
                    )
                    if (
                        len(current) >= 5
                        or sum(r["bytes"] for r in current) + size > 31457280
                    ):
                        raise AccessError(
                            413, "payload_too_large", "Session document limit reached"
                        )
                    if sum(r["question_id"] == question_id for r in current) >= (
                        q.constraints.max_files
                        if q.constraints.max_files is not None
                        else 5
                    ):
                        raise AccessError(
                            422, "invalid_upload", "Question document limit reached"
                        )
                    row = dict(
                        id=uuid4(),
                        session_id=session_id,
                        question_id=question_id,
                        filename=filename,
                        media_type=media,
                        bytes=size,
                        sha256=digest.hexdigest(),
                        storage_key=key,
                        state="ready",
                        created_at=now(db),
                        expires_at=session["expires_at"],
                    )
                    db.execute(uploads.insert().values(**row))
                    return Upload(**{k: row[k] for k in Upload.model_fields})

            persistence_attempted = True
            return await run_in_threadpool(persist)
        except BaseException:
            if not persistence_attempted:
                path.unlink(missing_ok=True)
            raise

    @router.post(
        "/upload-sessions/{session_id}/files",
        response_model=Upload,
        status_code=201,
        operation_id="upload_file",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "required": ["question_id", "file"],
                            "additionalProperties": False,
                            "properties": {
                                "question_id": {"type": "string", "format": "uuid"},
                                "file": {"type": "string", "format": "binary"},
                            },
                        }
                    }
                },
            }
        },
    )
    async def upload_file(
        session_id: UUID,
        request: Request,
        response: Response,
        x_upload_token: str | None = Header(None),
    ):
        result = await save(request, session_id, x_upload_token, "real")
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.post(
        "/test-upload-sessions/{session_id}/files",
        response_model=Upload,
        status_code=201,
        operation_id="upload_test_file",
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "required": ["question_id", "file"],
                            "additionalProperties": False,
                            "properties": {
                                "question_id": {"type": "string", "format": "uuid"},
                                "file": {"type": "string", "format": "binary"},
                            },
                        }
                    }
                },
            }
        },
    )
    async def upload_test_file(
        session_id: UUID,
        request: Request,
        response: Response,
        x_upload_token: str | None = Header(None),
        session=Depends(write_guard),
    ):
        result = await save(
            request, session_id, x_upload_token, "test", session["reviewer_id"]
        )
        response.headers["Cache-Control"] = "no-store"
        return result

    @router.get(
        "/uploads/{upload_id}/download",
        operation_id="download_upload",
        response_class=FileResponse,
    )
    def download(upload_id: UUID, session=Depends(read_guard)):
        with engine.connect() as db:
            row = (
                db.execute(select(uploads).where(uploads.c.id == upload_id))
                .mappings()
                .first()
            )
            if not row or not row["application_id"]:
                raise AccessError(404, "not_found", "Document unavailable")
            owned_application(db, row["application_id"], session["reviewer_id"])
        path = storage_path(settings, row["storage_key"])
        if not path.is_file():
            raise AccessError(404, "document_unavailable", "Document unavailable")
        return FileResponse(
            path,
            media_type=row["media_type"],
            filename=row["filename"],
            content_disposition_type="attachment",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "sandbox; default-src 'none'",
            },
        )

    return router
