import argparse
import logging
import signal
import threading
import time
from queue import Empty, Queue
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from talent_engine.config import Settings
from talent_engine.database import build_engine
from talent_engine.documents.cleanup import collect
from talent_engine.main import create_app

from .processor import StepFailure, process
from .queue import acquire, complete, event, fail, heartbeat
from .settings import WorkerSettings


def work_once(engine, settings, worker_id, *, processor=process):
    claim = acquire(engine, settings, worker_id)
    if not claim:
        return False
    stop = threading.Event()
    lost = threading.Event()
    output = Queue(maxsize=1)

    def renew():
        while not stop.wait(settings.heartbeat_seconds):
            try:
                if not heartbeat(engine, settings, claim):
                    lost.set()
                    return
            except SQLAlchemyError:
                lost.set()
                event("heartbeat_unavailable", claim)
                return

    def compute():
        try:
            output.put((True, processor(engine, claim)))
        except Exception as error:
            output.put((False, error))

    renewal = threading.Thread(target=renew, daemon=True)
    computation = threading.Thread(target=compute, daemon=True)
    renewal.start()
    computation.start()
    try:
        valid, result = output.get(timeout=settings.step_timeout_seconds)
        if lost.is_set():
            event("lease_lost", claim)
            return True
        if valid:
            complete(engine, settings, claim, result)
        elif isinstance(result, StepFailure):
            fail(
                engine,
                settings,
                claim,
                result.code,
                retryable=result.retryable,
                retry_after=result.retry_after,
            )
        elif isinstance(result, SQLAlchemyError):
            fail(engine, settings, claim, "database_unavailable", retryable=True)
        else:
            fail(engine, settings, claim, "step_failed", retryable=False)
    except Empty:
        fail(engine, settings, claim, "step_timeout", retryable=True)
    finally:
        stop.set()
        renewal.join(timeout=4)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Persistent PostgreSQL analysis worker"
    )
    parser.add_argument(
        "--once", action="store_true", help="Process at most one eligible step"
    )
    parser.add_argument(
        "--drain", action="store_true", help="Process eligible steps then exit"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings()
    worker_settings = WorkerSettings()
    engine = build_engine(settings)
    create_app(settings, engine=engine)  # Register the complete persistence schema.
    worker_id = "worker-" + uuid4().hex
    stopping = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stopping.set())
    signal.signal(signal.SIGINT, lambda *_: stopping.set())
    cleanup_at = 0.0
    event("worker_started", worker_id=worker_id)
    try:
        while not stopping.is_set():
            try:
                if time.monotonic() >= cleanup_at:
                    removed = collect(engine, settings)
                    if removed:
                        event("temporary_files_collected", count=removed)
                    cleanup_at = time.monotonic() + 3600
                worked = work_once(engine, worker_settings, worker_id)
                if args.once or (args.drain and not worked):
                    break
            except SQLAlchemyError:
                event("worker_database_unavailable", worker_id=worker_id)
                if args.once or args.drain:
                    raise SystemExit(1) from None
                worked = False
            except OSError:
                event("private_storage_unavailable", worker_id=worker_id)
                cleanup_at = time.monotonic() + 60
                worked = False
            if not worked:
                stopping.wait(worker_settings.poll_seconds)
    finally:
        engine.dispose()
        event("worker_stopped", worker_id=worker_id)


if __name__ == "__main__":
    main()
