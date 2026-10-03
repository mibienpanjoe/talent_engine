import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from talent_engine.config import Settings
from talent_engine.main import create_app


def test_liveness_does_not_depend_on_database():
    settings = Settings(
        database_url="postgresql+psycopg://hidden:db-password-marker@127.0.0.1:1/absent",
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-" + "x" * 32,
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health/live").json() == {"status": "alive"}
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        assert "db-password-marker" not in response.text
        assert "127.0.0.1" not in response.text


def test_configuration_requires_postgresql_and_hides_credentials():
    with pytest.raises(ValidationError):
        Settings(
            public_origin="http://localhost:3003",
            local_development=True,
            csrf_secret="test-only-" + "x" * 32,
            database_url="sqlite:///local.db",
        )
    settings = Settings(
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-" + "x" * 32,
        database_url="postgresql+psycopg://hidden:db-password-marker@localhost/db",
    )
    assert "db-password-marker" not in repr(settings)


@pytest.mark.parametrize("origin", ["http://public.example", "http://localhost/path"])
def test_local_mode_rejects_non_loopback_or_path_origin(origin):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://unused@localhost/db",
            public_origin=origin,
            local_development=True,
            csrf_secret="test-only-" + "x" * 32,
        )
