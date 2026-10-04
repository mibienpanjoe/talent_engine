from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

steps = Table(
    "analysis_steps",
    metadata,
    Column("run_id", Uuid, ForeignKey("analysis_runs.id"), primary_key=True),
    Column("name", String(50), primary_key=True),
    Column("position", Integer, nullable=False),
    Column("state", String(20), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("active_seconds", Float, nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("input_hash", String(64)),
    Column("output", JSONB),
    Column("error_code", String(100)),
    CheckConstraint("attempts >= 0 AND attempts <= 3", name="ck_step_attempts"),
    CheckConstraint("active_seconds >= 0", name="ck_step_active_seconds"),
)
