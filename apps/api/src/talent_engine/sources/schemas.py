from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field
from talent_engine.campaigns.schemas import Model


class AnswerLocator(Model):
    kind: Literal["answer"]
    question_id: UUID
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class PDFLocator(Model):
    kind: Literal["pdf"]
    page: int = Field(ge=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    method: Literal["text", "ocr"] = "text"


class WebLocator(Model):
    kind: Literal["web"]
    url: str = Field(max_length=2048)
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class WebCollection(Model):
    url: str = Field(max_length=2048)
    fetched_at: datetime
    status: Literal["succeeded", "failed"]
    http_status: int | None = None
    content_hash: str | None = None
    error_code: str | None = None


class OCRAttempt(Model):
    page: int = Field(ge=1, le=30)
    method: Literal["ocr"]
    prompt_version: str
    status: Literal["succeeded", "failed"]
    started_at: datetime
    finished_at: datetime
    error_code: str | None = None
    image_hash: str | None = None
    text_hash: str | None = None
    requested_model: str | None = None
    provider: str | None = None
    effective_model: str | None = None
    response_model: str | None = None
    duration_seconds: float | None = None


class ExtractionMetadata(Model):
    ocr: list[OCRAttempt] = Field(default_factory=list, max_length=30)
    web: list[WebCollection] = Field(default_factory=list, max_length=3)
    source_url: str | None = Field(default=None, max_length=2048)


class Evidence(Model):
    id: UUID
    source_version_id: UUID
    text: str
    locator: Annotated[
        AnswerLocator | PDFLocator | WebLocator, Field(discriminator="kind")
    ]
    nature: Literal[
        "declaration",
        "contextual_explanation",
        "consultable_artifact",
        "human_verification",
    ]
    excerpt_hash: str


class SourceVersion(Model):
    id: UUID
    kind: Literal["answer", "document", "portfolio", "github", "human_note"]
    question_ids: list[UUID]
    upload_id: UUID | None
    content_hash: str
    text_hash: str
    extractor_version: str
    state: Literal["available", "unavailable", "unreadable", "blocked"]
    error_code: str | None
    ocr_pages: list[int]
    extraction_metadata: ExtractionMetadata = Field(default_factory=ExtractionMetadata)
