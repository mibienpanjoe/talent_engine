import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from talent_engine.access import metadata, seed_reviewer
from talent_engine.config import Settings
from talent_engine.main import create_app


@pytest.fixture
def context():
    url = os.environ["TALENT_TEST_DATABASE_URL"]
    schema = "test_" + uuid4().hex
    admin = create_engine(url)
    assert admin.url.database.endswith("_test"), "Use an isolated test database"
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-c search_path={schema}"})
    metadata.create_all(engine)
    settings = Settings(
        database_url=url,
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-csrf-" + "x" * 32,
    )
    seed_reviewer(engine, "reviewer", "test-only-password")
    try:
        with TestClient(create_app(settings, engine=engine)) as client:
            yield client, engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
