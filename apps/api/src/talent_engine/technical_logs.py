"""Private worker logs, rotated hourly and collected after seven days."""

import logging
import os
import re
import time
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class PrivateLogHandler(TimedRotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        os.chmod(self.baseFilename, 0o600)


def configure_logs(directory):
    if directory is None:
        return None
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory.chmod(0o700)
    handler = PrivateLogHandler(
        directory / "worker.jsonl", when="H", utc=True, backupCount=168
    )
    os.chmod(handler.baseFilename, 0o600)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("talent_engine.worker")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    collect_logs(handler)
    return handler


def collect_logs(handler):
    if handler is None:
        return
    if handler.shouldRollover(None):
        handler.doRollover()
        os.chmod(handler.baseFilename, 0o600)
    current = Path(handler.baseFilename)
    threshold = time.time() - 7 * 86400
    for path in current.parent.glob("worker.jsonl.*"):
        if re.fullmatch(r"worker\.jsonl\.\d{4}-\d{2}-\d{2}_\d{2}", path.name):
            if (
                datetime.strptime(
                    path.name.removeprefix("worker.jsonl."), "%Y-%m-%d_%H"
                )
                .replace(tzinfo=timezone.utc)
                .timestamp()
                <= threshold
            ):
                path.unlink(missing_ok=True)
