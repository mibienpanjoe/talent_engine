import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from talent_engine.config import Settings
from talent_engine.main import create_app


def test_liveness_does_not_depend_on_database():
    settings = Settings(
        database_url="postgresql+psycopg://hidden:secret@127.0.0.1:1/absent"
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health/live").json() == {"status": "alive"}
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert "secret" not in response.text
        assert "127.0.0.1" not in response.text


def test_configuration_requires_postgresql_and_hides_credentials():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///local.db")
    settings = Settings(database_url="postgresql+psycopg://hidden:secret@localhost/db")
    assert "secret" not in repr(settings)
