from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TALENT_WORKER_", extra="ignore")
    lease_seconds: float = Field(default=90, ge=1, le=300)
    heartbeat_seconds: float = Field(default=30, ge=0.1, le=60)
    step_timeout_seconds: float = Field(default=60, ge=0.1, le=60)
    run_budget_seconds: float = Field(default=600, ge=1, le=600)
    retry_base_seconds: float = Field(default=30, ge=0, le=30)
    retry_second_seconds: float = Field(default=120, ge=0, le=120)
    poll_seconds: float = Field(default=1, ge=0.1, le=30)

    @model_validator(mode="after")
    def valid_lease(self):
        if self.heartbeat_seconds * 2 > self.lease_seconds:
            raise ValueError("Heartbeat must run at least twice per lease")
        return self
