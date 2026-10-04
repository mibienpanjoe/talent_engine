"""Local operator entrypoint. No credentials or candidate content are logged."""

import argparse
import json
import os
from pathlib import Path

from talent_engine.config import Settings
from talent_engine.database import build_engine
from talent_engine.schema import register_models

from .seeding import seed


def main():
    parser = argparse.ArgumentParser(
        description="Create identified fictitious demonstrations"
    )
    parser.add_argument("--mode", choices=["preloaded", "live"], default="preloaded")
    parser.add_argument(
        "--batch",
        default="default",
        help="Reuse a batch to avoid duplicates; choose a new one for new dossiers",
    )
    parser.add_argument("--fixtures", type=Path, default=Path("/app/fixtures"))
    parser.add_argument(
        "--portfolio",
        help="Optional public reference for the fictitious live development dossier",
    )
    parser.add_argument(
        "--github",
        help="Optional public repository for the fictitious development dossier",
    )
    args = parser.parse_args()
    settings = Settings()
    register_models()
    engine = build_engine(settings)
    try:
        results = seed(
            engine,
            settings,
            login=os.environ.get("TALENT_REVIEWER_LOGIN", ""),
            mode=args.mode,
            batch=args.batch,
            fixture_root=args.fixtures,
            portfolio=args.portfolio,
            github=args.github,
        )
    except Exception:
        raise SystemExit(
            "Demo seed failed; check mode, reviewer, migrations and fixture files."
        ) from None
    finally:
        engine.dispose()
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
