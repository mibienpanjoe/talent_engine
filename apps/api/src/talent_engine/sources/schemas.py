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


class Evidence(Model):
    id: UUID
    source_version_id: UUID
    text: str
    locator: Annotated[AnswerLocator | PDFLocator, Field(discriminator="kind")]
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
