from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TALENT_", hide_input_in_errors=True)
    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            valid = url.drivername == "postgresql+psycopg" and bool(
                url.host and url.database
            )
        except (ArgumentError, ValueError):
            valid = False
        if not valid:
            raise ValueError("A PostgreSQL psycopg connection URL is required")
        return value
