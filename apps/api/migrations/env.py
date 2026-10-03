from alembic import context
from talent_engine.config import Settings
from talent_engine.database import build_engine

# No ORM schema yet: domain tables arrive with their own migrations.
target_metadata = None


def run_migrations():
    settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url.get_secret_value(),
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = build_engine(settings)
        try:
            with engine.connect() as connection:
                context.configure(
                    connection=connection, target_metadata=target_metadata
                )
                with context.begin_transaction():
                    context.run_migrations()
        finally:
            engine.dispose()


run_migrations()
