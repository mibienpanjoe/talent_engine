import re
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import EmailStr, Field, StrictFloat, StrictInt, StrictStr, field_validator
from talent_engine.campaigns.lifecycle import PublishedSnapshot
from talent_engine.campaigns.schemas import Model
from talent_engine.documents.schemas import Upload


class Contact(Model):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr = Field(max_length=320)

    @field_validator("name")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("Name required")
        return value


class AnswerBase(Model):
    question_id: UUID


class ShortAnswer(AnswerBase):
    kind: Literal["short_text"]
    value: StrictStr = Field(max_length=500)


class LongAnswer(AnswerBase):
    kind: Literal["long_text"]
    value: StrictStr = Field(max_length=10000)


class EmailAnswer(AnswerBase):
    kind: Literal["email"]
    value: EmailStr = Field(max_length=320)


class NumberAnswer(AnswerBase):
    kind: Literal["number"]
    value: StrictFloat | StrictInt

    @field_validator("value")
    @classmethod
    def finite_precision(cls, value):
        number = Decimal(str(value))
        digits = "".join(str(x) for x in number.as_tuple().digits).rstrip("0")
        if (
            not number.is_finite()
            or number.copy_abs() > Decimal("1.7976931348623157e308")
            or len(digits) > 15
        ):
            raise ValueError(
                "Finite number with at most 15 significant digits required"
            )
        return value


class DateAnswer(AnswerBase):
    kind: Literal["date"]
    value: StrictStr

    @field_validator("value")
    @classmethod
    def iso_date(cls, value):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("ISO date required")
        date.fromisoformat(value)
        return value


class ChoiceAnswer(AnswerBase):
    kind: Literal["single_choice"]
    value: UUID


class ChoicesAnswer(AnswerBase):
    kind: Literal["multiple_choice"]
    value: list[UUID] = Field(max_length=20)

    @field_validator("value")
    @classmethod
    def distinct(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate options")
        return value


class UrlAnswer(AnswerBase):
    kind: Literal["url"]
    value: StrictStr = Field(max_length=2048)

    @field_validator("value")
    @classmethod
    def valid_url(cls, value):
        url = urlsplit(value)
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or any(ord(x) < 33 for x in value)
        ):
            raise ValueError("HTTP(S) URL required")
        _ = url.port
        return value


class FileAnswer(AnswerBase):
    kind: Literal["file"]
    value: list[UUID] = Field(max_length=5)


Answer = Annotated[
    ShortAnswer
    | LongAnswer
    | EmailAnswer
    | NumberAnswer
    | DateAnswer
    | ChoiceAnswer
    | ChoicesAnswer
    | UrlAnswer
    | FileAnswer,
    Field(discriminator="kind"),
]


class SubmissionInput(Model):
    snapshot_id: UUID
    contact: Contact
    answers: list[Answer] = Field(max_length=50)
    upload_session_id: UUID | None = None
    upload_token: str | None = Field(default=None, min_length=43, max_length=200)


class Receipt(Model):
    receipt_ref: str
    received_at: datetime


class ApplicationSummary(Model):
    id: UUID
    campaign_id: UUID
    snapshot_id: UUID
    mode: Literal["real", "test"]
    contact: Contact
    received_at: datetime
    processing_state: Literal[
        "queued", "collecting", "evaluating", "completed", "completed_partial", "failed"
    ]
    decision: Literal["to_review", "shortlisted", "not_selected"]
    review_revision: int
    effective_evaluation_id: UUID | None = None
    calculation: None = None
    eligibility: None = None
    rank: None = None
    views: list[str] = Field(default_factory=lambda: ["all", "needs_review"])


class ApplicationPage(Model):
    items: list[ApplicationSummary]
    next_cursor: str | None
    list_revision: str
    counts: dict[str, int]


class ApplicationDetail(Model):
    snapshot: PublishedSnapshot
    application: ApplicationSummary
    answers: list[Answer]
    effective_evaluation: None = None
    pending_evaluation_ids: list[UUID] = Field(default_factory=list)
    uploads: list[Upload] = Field(default_factory=list)
