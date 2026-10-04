import re

from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from talent_engine.errors import AccessError, error_payload

from .service import requests

PUBLIC = re.compile(
    r"^/api/v1/public/campaigns/([^/]{1,64})/(applications|upload-sessions)$"
)
FILES = re.compile(r"^/api/v1/(test-)?upload-sessions/[^/]+/files$")


class PublicLimits:
    def __init__(self, app, engine, settings):
        self.app, self.engine, self.settings = app, engine, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        ip = scope["client"][0] if scope.get("client") else "unknown"
        match = PUBLIC.fullmatch(scope["path"])
        if match and match[2] == "applications":
            scopes = [
                (f"submission-ip:{ip}", 10),
                (f"submission-campaign:{match[1]}", 100),
            ]
        elif match:
            scopes = [(f"upload-session-ip:{ip}", 10)]
        elif FILES.fullmatch(scope["path"]):
            scopes = [(f"upload-ip:{ip}", 20)]
        else:
            return await self.app(scope, receive, send)
        try:
            await run_in_threadpool(requests, self.engine, self.settings, scopes)
        except AccessError as error:
            return await JSONResponse(
                error_payload(error.code, error.message),
                status_code=429,
                headers={
                    "Cache-Control": "no-store",
                    "Retry-After": str(error.retry_after),
                },
            )(scope, receive, send)
        except SQLAlchemyError:
            return await JSONResponse(
                error_payload("service_unavailable", "Database unavailable"),
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )(scope, receive, send)
        return await self.app(scope, receive, send)
