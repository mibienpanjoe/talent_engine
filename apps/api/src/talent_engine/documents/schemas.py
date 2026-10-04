from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from talent_engine.campaigns.schemas import Model


class UploadSessionInput(Model):
    snapshot_id: UUID


class UploadSessionCreated(Model):
    id: UUID
    snapshot_id: UUID
    upload_token: str
    expires_at: datetime


class Upload(Model):
    id: UUID
    question_id: UUID
    filename: str = Field(max_length=200)
    media_type: Literal["application/pdf", "image/png", "image/jpeg"]
    bytes: int = Field(ge=1, le=10485760)
    sha256: str = Field(pattern="^[a-f0-9]{64}$")
