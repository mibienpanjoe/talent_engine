"""Run after `alembic upgrade head` against an isolated PostgreSQL database."""

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import text
from talent_engine.config import Settings
from talent_engine.database import build_engine
from talent_engine.main import create_app

settings = Settings()
engine = build_engine(settings)
with engine.connect() as connection:
    assert (
        connection.scalar(text("SELECT version_num FROM alembic_version"))
        == ScriptDirectory.from_config(
            Config("apps/api/alembic.ini")
        ).get_current_head()
    )
engine.dispose()
with TestClient(create_app(settings)) as client:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ready"}
print("PostgreSQL migration and API readiness verified")
