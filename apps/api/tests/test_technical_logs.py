import logging
import os
import time
from datetime import datetime, timezone

from talent_engine.technical_logs import collect_logs, configure_logs


def test_private_logs_expire_without_removing_other_files(tmp_path):
    old = tmp_path / "worker.jsonl"
    old.write_text('{"event":"old"}\n')
    os.utime(old, (time.time() - 9 * 86400,) * 2)
    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep")
    recent_name = datetime.now(timezone.utc).strftime("worker.jsonl.%Y-%m-%d_%H")
    recent = tmp_path / recent_name
    recent.write_text('{"event":"recent"}\n')
    logger = logging.getLogger("talent_engine.worker")
    handlers, propagate, level = logger.handlers[:], logger.propagate, logger.level
    handler = configure_logs(tmp_path)
    try:
        logger.info('{"event":"cleanup_completed","request_id":"synthetic"}')
        handler.flush()
        collect_logs(handler)
        assert old.stat().st_mode & 0o777 == 0o600
        assert tmp_path.stat().st_mode & 0o777 == 0o700
        assert "old" not in old.read_text()
        assert "cleanup_completed" in old.read_text()
        assert recent.exists() and unrelated.exists()
        assert len(list(tmp_path.glob("worker.jsonl.*"))) == 1
        handler.rolloverAt = 0
        logger.info('{"event":"new"}')
        assert old.stat().st_mode & 0o777 == 0o600
    finally:
        handler.close()
        logger.handlers = handlers
        logger.propagate, logger.level = propagate, level
