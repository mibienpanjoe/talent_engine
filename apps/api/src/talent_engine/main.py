from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException

from talent_engine.access import build_access_router
from talent_engine.analyses.data import steps
from talent_engine.applications.router import build_application_router
from talent_engine.body_limit import BodyLimit
from talent_engine.campaigns.lifecycle import build_lifecycle_router
from talent_engine.campaigns.router import build_campaign_router
from talent_engine.config import Settings
from talent_engine.database import build_engine
from talent_engine.deletions.router import build_deletion_router
from talent_engine.documents.router import build_document_router
from talent_engine.errors import AccessError, Error, ErrorDetail, error_payload
from talent_engine.evaluations.data import evaluations
from talent_engine.reception_limits.middleware import PublicLimits
from talent_engine.reviews.router import build_review_router
from talent_engine.sources.data import sources


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["alive", "ready"]


def create_app(
    settings: Settings | None = None, *, engine: Engine | None = None
) -> FastAPI:
    _ = steps, sources, evaluations  # Register shared persistence schema.
    settings = settings or Settings()
    engine = engine or build_engine(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Talent Engine", version="0.1.0", lifespan=lifespan)

    app.include_router(build_access_router(engine, settings))
    app.include_router(build_campaign_router(engine, settings))
    app.include_router(build_lifecycle_router(engine, settings))
    app.include_router(build_application_router(engine, settings))
    app.include_router(build_document_router(engine, settings))
    app.include_router(build_review_router(engine, settings))
    app.include_router(build_deletion_router(engine, settings))
    app.add_middleware(BodyLimit)
    app.add_middleware(PublicLimits, engine=engine, settings=settings)

    @app.exception_handler(AccessError)
    async def access_error(request: Request, error: AccessError):
        headers = {"Cache-Control": "no-store"}
        if error.retry_after:
            headers["Retry-After"] = str(error.retry_after)
        return JSONResponse(
            status_code=error.status,
            content=error_payload(error.code, error.message, error.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "Invalid request",
                [
                    ErrorDetail(
                        path=".".join(str(x) for x in item["loc"])[:500],
                        code=item["type"][:100],
                    )
                    for item in error.errors()[:50]
                ],
            ),
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, error: SQLAlchemyError):
        return JSONResponse(
            status_code=503,
            content=error_payload("service_unavailable", "Database unavailable"),
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        code = "not_found" if error.status_code == 404 else "invalid_request"
        return JSONResponse(
            status_code=error.status_code,
            content=error_payload(code, "Request unavailable"),
        )

    @app.get(
        "/api/v1/health/live",
        response_model=Health,
        operation_id="health_live",
        tags=["health"],
    )
    def health_live() -> Health:
        return Health(status="alive")

    @app.get(
        "/api/v1/health/ready",
        response_model=Health,
        operation_id="health_ready",
        tags=["health"],
        responses={503: {"model": Error}},
    )
    def health_ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503,
                content=error_payload("service_unavailable", "Database unavailable"),
            )
        return Health(status="ready")

    return app
