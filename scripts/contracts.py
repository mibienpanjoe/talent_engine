"""Generate FastAPI contracts; compare without mutations in check mode."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
with tempfile.TemporaryDirectory() as directory:
    schema = Path(directory) / "openapi.json"
    client = Path(directory) / "api.generated.ts"
    python = os.environ.get(
        "TALENT_API_PYTHON", str(root / "apps/api/.venv/bin/python")
    )
    schema.write_bytes(
        subprocess.check_output(
            [python, "-m", "talent_engine.export_openapi"], cwd=root
        )
    )
    subprocess.run(
        ["pnpm", "exec", "openapi-typescript", str(schema), "-o", str(client)],
        cwd=root,
        check=True,
    )
    for generated, target in [
        (schema, root / "contracts/openapi.json"),
        (client, root / "apps/web/src/lib/api.generated.ts"),
    ]:
        if args.check:
            if not target.exists() or target.read_bytes() != generated.read_bytes():
                raise SystemExit(
                    f"Stale contract: {target.relative_to(root)}. "
                    "Run pnpm contracts:generate"
                )
        else:
            target.write_bytes(generated.read_bytes())
print("Contracts are current" if args.check else "Contracts generated")
