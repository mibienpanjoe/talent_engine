from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from talent_engine.database import metadata

sources = Table(
    "source_versions",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, ForeignKey("applications.id"), nullable=False),
    Column("source_key", String(100), nullable=False),
    Column("kind", String(20), nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("text_hash", String(64), nullable=False),
    Column("question_ids", JSONB, nullable=False),
    Column("upload_id", Uuid, ForeignKey("uploads.id")),
    Column("extractor_version", String(100), nullable=False),
    Column("state", String(20), nullable=False),
    Column("error_code", String(100)),
    Column("ocr_pages", JSONB, nullable=False),
    Column("pages", JSONB, nullable=False),
    Column("extraction_metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("id", "application_id"),
)
excerpts = Table(
    "evidence_excerpts",
    metadata,
    Column("id", Uuid, primary_key=True),
    Column("application_id", Uuid, ForeignKey("applications.id"), nullable=False),
    Column("source_version_id", Uuid, nullable=False),
    Column("text", Text, nullable=False),
    Column("locator", JSONB, nullable=False),
    Column("nature", String(30), nullable=False),
    Column("excerpt_hash", String(64), nullable=False),
    UniqueConstraint("id", "application_id"),
    ForeignKeyConstraint(
        ["source_version_id", "application_id"],
        ["source_versions.id", "source_versions.application_id"],
    ),
)
run_sources = Table(
    "run_sources",
    metadata,
    Column("run_id", Uuid, primary_key=True),
    Column("source_version_id", Uuid, primary_key=True),
    Column("application_id", Uuid, nullable=False),
    ForeignKeyConstraint(
        ["run_id", "application_id"],
        ["analysis_runs.id", "analysis_runs.application_id"],
    ),
    ForeignKeyConstraint(
        ["source_version_id", "application_id"],
        ["source_versions.id", "source_versions.application_id"],
    ),
)
run_evidence = Table(
    "run_evidence",
    metadata,
    Column("run_id", Uuid, primary_key=True),
    Column("excerpt_id", Uuid, primary_key=True),
    Column("application_id", Uuid, nullable=False),
    ForeignKeyConstraint(
        ["run_id", "application_id"],
        ["analysis_runs.id", "analysis_runs.application_id"],
    ),
    ForeignKeyConstraint(
        ["excerpt_id", "application_id"],
        ["evidence_excerpts.id", "evidence_excerpts.application_id"],
    ),
)
