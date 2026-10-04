from datetime import datetime
from typing import Literal
from uuid import UUID

from talent_engine.campaigns.schemas import Model


class Cleanup(Model):
    id: UUID
    application_id: UUID
    campaign_id: UUID
    state: Literal["pending", "waiting", "completed"]
    attempts: int
    incident: bool
    next_attempt_at: datetime | None
    error_code: str | None
    created_at: datetime
    completed_at: datetime | None
