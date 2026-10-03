from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from talent_engine.config import Settings
from talent_engine.database import build_engine


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["alive", "ready"]


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    message: str
    request_id: str
    details: list[dict[str, str]]


class Error(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorBody


def create_app(settings: Settings | None = None) -> FastAPI:
    engine = build_engine(settings or Settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Talent Engine", version="0.1.0", lifespan=lifespan)

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
            error = Error(
                error=ErrorBody(
                    code="service_unavailable",
                    message="Database unavailable",
                    request_id=str(uuid4()),
                    details=[],
                )
            )
            return JSONResponse(status_code=503, content=error.model_dump())
        return Health(status="ready")

    return app
