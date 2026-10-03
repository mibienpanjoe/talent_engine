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


def login(client):
    return client.post(
        "/api/v1/access/session",
        headers={"Origin": "http://localhost:3003"},
        json={"login": "reviewer", "password": "test-only-password"},
    )


def test_login_stable_csrf_and_logout(context):
    client, engine = context
    assert client.get("/api/v1/access/session").status_code == 401
    response = login(client)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert "domain=" not in cookie
    csrf = response.json()["csrf_token"]
    assert client.get("/api/v1/access/csrf").json()["csrf_token"] == csrf
    assert client.get("/api/v1/access/csrf").json()["csrf_token"] == csrf
    assert (
        client.delete(
            "/api/v1/access/session",
            headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert (
        client.delete(
            "/api/v1/access/session", headers={"Origin": "http://localhost:3003"}
        ).status_code
        == 403
    )
    assert client.get("/api/v1/access/session").status_code == 200
    assert (
        client.delete(
            "/api/v1/access/session",
            headers={"Origin": "http://localhost:3003", "X-CSRF-Token": csrf},
        ).status_code
        == 204
    )
    assert client.get("/api/v1/access/session").status_code == 401
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT revoked_at IS NOT NULL FROM sessions"))


@pytest.mark.parametrize("expired_field", ["expires_at", "last_seen_at"])
def test_expired_session_cannot_read_private_data(context, expired_field):
    client, engine = context
    assert login(client).status_code == 200
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE sessions SET {expired_field} = now() - interval '9 hours'")
        )
    assert client.get("/api/v1/access/session").status_code == 401


def test_hostile_login_validation_and_shared_limit(context):
    client, _ = context
    assert (
        client.post(
            "/api/v1/access/session",
            headers={"Origin": "https://evil.example"},
            json={"login": "reviewer", "password": "test-only-password"},
        ).status_code
        == 403
    )
    response = client.post(
        "/api/v1/access/session", json={"password": "never-echo-this"}
    )
    assert response.status_code == 422 and "never-echo-this" not in response.text
    for _ in range(5):
        response = client.post(
            "/api/v1/access/session",
            headers={"Origin": "http://localhost:3003"},
            json={"login": "reviewer", "password": "wrong"},
        )
        assert response.status_code == 401
    response = login(client)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0


def test_password_rotation_revokes_existing_sessions(context):
    client, engine = context
    assert login(client).status_code == 200
    seed_reviewer(engine, "reviewer", "replacement-test-password")
    assert client.get("/api/v1/access/session").status_code == 401
    with engine.connect() as connection:
        assert connection.scalar(
            text("SELECT password_hash FROM reviewers")
        ).startswith("$argon2id$")


def test_parallel_attempts_cannot_bypass_shared_limit(context):
    from concurrent.futures import ThreadPoolExecutor

    client, _ = context

    def attempt(_):
        return client.post(
            "/api/v1/access/session",
            headers={"Origin": "http://localhost:3003"},
            json={"login": "reviewer", "password": "wrong"},
        ).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(attempt, range(10)))
    assert statuses.count(401) == 5
    assert statuses.count(429) == 5


def test_https_uses_host_cookie_and_secure_transport(context):
    _, engine = context
    settings = Settings(
        database_url=os.environ["TALENT_TEST_DATABASE_URL"],
        public_origin="https://talent.example",
        csrf_secret="test-only-" + "x" * 32,
    )
    with TestClient(
        create_app(settings, engine=engine), base_url="https://talent.example"
    ) as client:
        response = client.post(
            "/api/v1/access/session",
            headers={"Origin": "https://talent.example"},
            json={"login": "reviewer", "password": "test-only-password"},
        )
        assert response.status_code == 200
        assert "__Host-talent_session=" in response.headers["set-cookie"]
        assert "Secure" in response.headers["set-cookie"]
        assert client.get("/api/v1/access/session").status_code == 200
        assert (
            client.get("http://talent.example/api/v1/access/session").status_code == 401
        )
