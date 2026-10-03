from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class DatabaseSettings(BaseSettings):
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


class Settings(DatabaseSettings):
    public_origin: str
    local_development: bool = False
    csrf_secret: SecretStr

    @field_validator("csrf_secret")
    @classmethod
    def require_csrf_secret(cls, value: SecretStr) -> SecretStr:
        if not 32 <= len(value.get_secret_value()) <= 2048:
            raise ValueError("CSRF secret must contain at least 32 characters")
        return value

    @model_validator(mode="after")
    def validate_origin(self):
        url = urlsplit(self.public_origin)
        _ = url.port  # Validate explicit ports.
        if (
            not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError("Configure an origin without path or credentials")
        if self.local_development:
            if url.scheme != "http" or url.hostname not in {
                "localhost",
                "127.0.0.1",
                "::1",
            }:
                raise ValueError("Local HTTP requires a loopback origin")
        elif url.scheme != "https":
            raise ValueError("HTTPS is required outside local development")
        return self
