"""Initialize or rotate the single demo reviewer from private environment values."""

import os

from talent_engine.access import seed_reviewer
from talent_engine.config import DatabaseSettings
from talent_engine.database import build_engine

engine = build_engine(DatabaseSettings())
try:
    seed_reviewer(
        engine,
        os.environ["TALENT_REVIEWER_LOGIN"],
        os.environ["TALENT_REVIEWER_PASSWORD"],
    )
finally:
    engine.dispose()
print("Reviewer initialized; existing sessions revoked on password rotation")
