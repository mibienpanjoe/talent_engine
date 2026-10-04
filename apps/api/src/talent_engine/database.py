from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine

from talent_engine.config import DatabaseSettings

metadata = MetaData()


def build_engine(settings: DatabaseSettings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=3,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        hide_parameters=True,
        echo=False,
    )
