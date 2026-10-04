from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Table,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

projections = Table(
    "review_projections",
    metadata,
    Column("evaluation_id", Uuid, primary_key=True),
    Column("application_id", Uuid, nullable=False),
    Column("assessments", JSONB, nullable=False),
    Column("conditions", JSONB, nullable=False),
    Column("eligibility", String(30), nullable=False),
    Column("calculation", JSONB, nullable=False),
    Column("score_numerator", Numeric(100, 0)),
    Column("score_denominator", Numeric(100, 0)),
    ForeignKeyConstraint(
        ["evaluation_id", "application_id"],
        ["evaluations.id", "evaluations.application_id"],
    ),
)
events = Table(
    "review_events",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, ForeignKey("applications.id"), nullable=False),
    Column("evaluation_id", Uuid),
    Column("author_id", Uuid, ForeignKey("reviewers.id"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("review_revision", BigInteger, nullable=False),
    Column("kind", String(30), nullable=False),
    Column("criterion_id", Uuid),
    Column("action", String(30), nullable=False),
    Column("reason", String(2000), nullable=False),
    Column("previous", JSONB, nullable=False),
    Column("value", JSONB, nullable=False),
    Column("origin_event_id", Uuid, ForeignKey("review_events.id")),
    ForeignKeyConstraint(
        ["evaluation_id", "application_id"],
        ["evaluations.id", "evaluations.application_id"],
    ),
)

application_actions = Table(
    "application_actions",
    metadata,
    Column("application_id", Uuid, ForeignKey("applications.id"), primary_key=True),
    Column("route", String(30), primary_key=True),
    Column("key_digest", String(64), primary_key=True),
    Column("payload_hash", String(64), nullable=False),
    Column("result_id", Uuid, nullable=False),
    Column("request", JSONB),
    Column("expires_at", DateTime(timezone=True)),
)

Index("ix_review_history", events.c.application_id, events.c.created_at, events.c.id)
