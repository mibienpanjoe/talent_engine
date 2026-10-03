"""Bound JSON before parsing; document streaming has its own bounded path."""

import asyncio
from collections import deque

from starlette.responses import JSONResponse

from talent_engine.errors import error_payload


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in ("POST", "PATCH", "PUT"):
            return await self.app(scope, receive, send)
        limit = (
            262144
            if scope["path"].endswith("/applications")
            or scope["path"].endswith("/test-applications")
            else 1048576
        )
        messages = deque()
        size = 0
        try:
            async with asyncio.timeout(30):
                while True:
                    message = await receive()
                    if message["type"] != "http.request":
                        return
                    size += len(message.get("body", b""))
                    if size > limit:
                        return await JSONResponse(
                            error_payload(
                                "payload_too_large", "Request exceeds allowed size"
                            ),
                            status_code=413,
                        )(scope, receive, send)
                    messages.append(message)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            return await JSONResponse(
                error_payload("request_timeout", "Request timed out"), status_code=408
            )(scope, receive, send)

        async def bounded_receive():
            return messages.popleft() if messages else await receive()

        await self.app(scope, bounded_receive, send)
