from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from talent_engine.campaigns.schemas import Model


class StepProgress(Model):
    name: str
    state: Literal["queued", "running", "waiting", "succeeded", "failed"]
    attempts: int = Field(ge=0, le=3)
    started_at: datetime | None
    finished_at: datetime | None
    error_code: str | None


class AnalysisProgress(Model):
    id: UUID
    reason: str
    state: str
    error_code: str | None
    next_attempt_at: datetime | None
    steps: list[StepProgress]
