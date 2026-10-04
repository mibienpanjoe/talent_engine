from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

evaluations = Table(
    "evaluations",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, nullable=False),
    Column("run_id", Uuid, unique=True, nullable=False),
    Column("snapshot_id", Uuid, nullable=False),
    Column("policy_version", String(100), nullable=False),
    Column("assessments", JSONB, nullable=False),
    Column("conditions", JSONB, nullable=False),
    Column("eligibility", String(30), nullable=False),
    Column("calculation", JSONB, nullable=False),
    Column("provenance", JSONB, nullable=False),
    Column("score_numerator", Numeric(100, 0)),
    Column("score_denominator", Numeric(100, 0)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("id", "application_id"),
    ForeignKeyConstraint(
        ["run_id", "application_id", "snapshot_id"],
        [
            "analysis_runs.id",
            "analysis_runs.application_id",
            "analysis_runs.snapshot_id",
        ],
    ),
)

embedding_cache = Table(
    "embedding_cache",
    metadata,
    Column(
        "application_id",
        Uuid,
        ForeignKey("applications.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("identity", String(64), primary_key=True),
    Column("input_hash", String(64), primary_key=True),
    Column("vector", JSONB, nullable=False),
)
