"""Single-reviewer access with PostgreSQL sessions and shared attempt counters."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Uuid,
    delete,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

from talent_engine.config import Settings
from talent_engine.errors import AccessError, Error

metadata = MetaData()
reviewers = Table(
    "reviewers",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("login", String(200), unique=True, nullable=False),
    Column("password_hash", String(500), nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    ),
    Column("disabled_at", DateTime(timezone=True)),
)
sessions = Table(
    "sessions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("reviewer_id", Uuid, ForeignKey("reviewers.id"), nullable=False),
    Column("token_digest", String(64), unique=True, nullable=False),
    Column("csrf_digest", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)
login_limits = Table(
    "login_limits",
    metadata,
    Column("key", String(64), primary_key=True),
    Column("attempts", Integer, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
)
hasher = PasswordHasher()


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login: str = Field(min_length=1, max_length=200)
    password: SecretStr = Field(min_length=1, max_length=1024)


class Reviewer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    login: str = Field(max_length=200)
    expires_at: datetime


class LoginResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer: Reviewer
    csrf_token: str = Field(min_length=32, max_length=200)


class CsrfToken(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csrf_token: str = Field(min_length=32, max_length=200)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_for(settings: Settings, session_id: UUID, token_digest: str) -> str:
    return hmac.new(
        settings.csrf_secret.get_secret_value().encode(),
        b"csrf-v1\0" + session_id.bytes + token_digest.encode(),
        hashlib.sha256,
    ).hexdigest()


def seed_reviewer(engine: Engine, login: str, password: str) -> None:
    if not 1 <= len(login) <= 200 or not 12 <= len(password) <= 1024:
        raise ValueError("Reviewer login and password length are invalid")
    password_hash = hasher.hash(password)
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(527412031)"))
        current = (
            connection.execute(
                select(reviewers).where(reviewers.c.login == login).with_for_update()
            )
            .mappings()
            .first()
        )
        if current:
            connection.execute(
                update(reviewers)
                .where(reviewers.c.id == current["id"])
                .values(password_hash=password_hash)
            )
            connection.execute(
                update(sessions)
                .where(sessions.c.reviewer_id == current["id"])
                .values(revoked_at=datetime.now(timezone.utc))
            )
        else:
            # A seed must not silently create extra demo accounts.
            if connection.scalar(select(reviewers.c.id).limit(1)):
                raise ValueError("A reviewer already exists")
            connection.execute(
                insert(reviewers).values(
                    id=uuid4(), login=login, password_hash=password_hash
                )
            )


def build_access_router(engine: Engine, settings: Settings) -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/access",
        tags=["access"],
        responses={401: {"model": Error}, 403: {"model": Error}, 429: {"model": Error}},
    )
    cookie_name = (
        "talent_session_dev" if settings.local_development else "__Host-talent_session"
    )
    dummy_hash = hasher.hash(secrets.token_hex(32))

    def require_origin(request: Request) -> None:
        if request.headers.get("origin") != settings.public_origin:
            raise AccessError(403, "forbidden", "Origin not allowed")

    def require_session(request: Request):
        token = request.cookies.get(cookie_name, "")
        if not token or len(token) > 128:
            raise AccessError(401, "unauthorized", "Sign in required")
        now = datetime.now(timezone.utc)
        with engine.begin() as connection:
            row = (
                connection.execute(
                    select(sessions, reviewers.c.login)
                    .join(reviewers)
                    .where(
                        (sessions.c.token_digest == digest(token))
                        & (reviewers.c.disabled_at.is_(None))
                    )
                    .with_for_update(of=sessions)
                )
                .mappings()
                .first()
            )
            if (
                not row
                or row["revoked_at"]
                or row["expires_at"] <= now
                or row["last_seen_at"] <= now - timedelta(hours=1)
            ):
                raise AccessError(401, "unauthorized", "Sign in required")
            connection.execute(
                update(sessions)
                .where(sessions.c.id == row["id"])
                .values(last_seen_at=now)
            )
        return row

    def require_mutation(request: Request, session=Depends(require_session)):
        require_origin(request)
        token = request.headers.get("x-csrf-token", "")
        expected = csrf_for(settings, session["id"], session["token_digest"])
        if not hmac.compare_digest(
            token.encode(), expected.encode()
        ) or not hmac.compare_digest(digest(token), session["csrf_digest"]):
            raise AccessError(403, "forbidden", "Invalid CSRF token")
        return session

    def reviewer_result(session) -> Reviewer:
        return Reviewer(
            id=session["reviewer_id"],
            login=session["login"],
            expires_at=session["expires_at"],
        )

    @router.post("/session", response_model=LoginResult, operation_id="login")
    def login(payload: LoginInput, request: Request, response: Response):
        require_origin(request)
        now = datetime.now(timezone.utc)
        # Do not trust forwarded IP headers; direct API access cannot forge a rate key.
        ip = request.client.host if request.client else "unknown"
        keys = sorted(
            hmac.new(
                settings.csrf_secret.get_secret_value().encode(),
                value.encode(),
                hashlib.sha256,
            ).hexdigest()
            for value in ["login-account:" + payload.login, "login-ip:" + ip]
        )
        blocked_until = None
        with engine.begin() as connection:
            connection.execute(
                delete(login_limits).where(login_limits.c.expires_at <= now)
            )
            for key in keys:
                row = (
                    connection.execute(
                        text("""
                    INSERT INTO login_limits (key, attempts, expires_at)
                    VALUES (:key, 1, :expires)
                    ON CONFLICT (key) DO UPDATE SET attempts = login_limits.attempts + 1
                    RETURNING attempts, expires_at
                """),
                        {"key": key, "expires": now + timedelta(minutes=15)},
                    )
                    .mappings()
                    .one()
                )
                if row["attempts"] > 5:
                    blocked_until = row["expires_at"]
        if blocked_until:
            raise AccessError(
                429,
                "rate_limited",
                "Too many sign-in attempts",
                max(1, int((blocked_until - now).total_seconds()) + 1),
            )
        with engine.begin() as connection:
            reviewer = (
                connection.execute(
                    select(reviewers)
                    .where(reviewers.c.login == payload.login)
                    .with_for_update()
                )
                .mappings()
                .first()
            )
            try:
                hasher.verify(
                    reviewer["password_hash"] if reviewer else dummy_hash,
                    payload.password.get_secret_value(),
                )
                valid = reviewer is not None and reviewer["disabled_at"] is None
            except (VerificationError, InvalidHashError):
                valid = False
            if not valid:
                raise AccessError(401, "unauthorized", "Invalid login or password")
            token, session_id = secrets.token_urlsafe(32), uuid4()
            token_digest = digest(token)
            csrf = csrf_for(settings, session_id, token_digest)
            expires_at = now + timedelta(hours=8)
            connection.execute(delete(sessions).where(sessions.c.expires_at <= now))
            connection.execute(
                insert(sessions).values(
                    id=session_id,
                    reviewer_id=reviewer["id"],
                    token_digest=token_digest,
                    csrf_digest=digest(csrf),
                    created_at=now,
                    expires_at=expires_at,
                    last_seen_at=now,
                )
            )
        response.set_cookie(
            cookie_name,
            token,
            max_age=8 * 3600,
            httponly=True,
            secure=not settings.local_development,
            samesite="lax",
            path="/",
        )
        response.headers["Cache-Control"] = "no-store"
        return LoginResult(
            reviewer=Reviewer(
                id=reviewer["id"], login=reviewer["login"], expires_at=expires_at
            ),
            csrf_token=csrf,
        )

    @router.get("/session", response_model=Reviewer, operation_id="session_me")
    def session_me(response: Response, session=Depends(require_session)):
        response.headers["Cache-Control"] = "no-store"
        return reviewer_result(session)

    @router.get("/csrf", response_model=CsrfToken, operation_id="csrf")
    def csrf(response: Response, session=Depends(require_session)):
        response.headers["Cache-Control"] = "no-store"
        return CsrfToken(
            csrf_token=csrf_for(settings, session["id"], session["token_digest"])
        )

    @router.delete("/session", status_code=204, operation_id="logout")
    def logout(response: Response, session=Depends(require_mutation)):
        with engine.begin() as connection:
            connection.execute(
                update(sessions)
                .where(sessions.c.id == session["id"])
                .values(revoked_at=datetime.now(timezone.utc))
            )
        response.delete_cookie(
            cookie_name,
            path="/",
            httponly=True,
            secure=not settings.local_development,
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"
        response.status_code = 204
        return response

    return router
