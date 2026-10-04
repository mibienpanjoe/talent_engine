from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(max_length=500)
    code: str = Field(max_length=100)


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=100)
    message: str = Field(max_length=2000)
    request_id: str = Field(max_length=100)
    details: list[ErrorDetail]


class Error(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorBody


def error_payload(
    code: str, message: str, details: list[ErrorDetail] | None = None
) -> dict:
    return Error(
        error=ErrorBody(
            code=code, message=message, request_id=str(uuid4()), details=details or []
        )
    ).model_dump()


class AccessError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        retry_after: int | None = None,
        *,
        details: list[ErrorDetail] | None = None,
    ):
        self.status, self.code, self.message = status, code, message
        self.retry_after = retry_after
        self.details = details or []
