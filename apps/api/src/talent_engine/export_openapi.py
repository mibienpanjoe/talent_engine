"""Export routes actually implemented without opening a database connection."""

import json
import sys

from talent_engine.config import Settings
from talent_engine.main import create_app

app = create_app(
    Settings(
        public_origin="http://localhost:3003",
        local_development=True,
        csrf_secret="test-only-" + "x" * 32,
        database_url="postgresql+psycopg://unused@localhost/unused",
    )
)
json.dump(app.openapi(), sys.stdout, ensure_ascii=False, sort_keys=True, indent=2)
sys.stdout.write("\n")
