import atexit
import datetime
import logging
import os
import queue
import sys
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from os import makedirs
from typing import Optional

from .files import get_logs_dir

_logging_initialized = False
_log_listener: Optional[QueueListener] = None


def _cleanup_logging() -> None:
    global _log_listener
    if _log_listener is not None:
        _log_listener.stop()
        _log_listener = None


atexit.register(_cleanup_logging)


def setup_logging(console_level_str: str = "INFO", file_level_str: str = "DEBUG") -> None:
    global _logging_initialized, _log_listener

    # Stop existing listener if we are reconfiguring
    if _log_listener is not None:
        _log_listener.stop()
        _log_listener = None

    root_logger = logging.getLogger()

    # Remove and close existing handlers to avoid duplicates and release file locks
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # 1. Console Handler
    console_level = getattr(logging, console_level_str.upper(), logging.INFO)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # 2. File Handler with startup rotation
    logs_dir = get_logs_dir()
    makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "skanlator.log")

    if not _logging_initialized:
        if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = os.path.join(logs_dir, f"skanlator_{timestamp}.log")
            try:
                os.rename(log_file, archive_name)
            except Exception as e:
                print(f"Failed to archive existing log file on startup: {e}", file=sys.stderr)
        _logging_initialized = True

    file_level = getattr(logging, file_level_str.upper(), logging.DEBUG)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB limit
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    # 3. Queue & QueueListener for Async Logging
    log_queue = queue.Queue(-1)  # Unlimited queue size
    _log_listener = QueueListener(log_queue, console_handler, file_handler, respect_handler_level=True)
    _log_listener.start()

    # The root logger writes to the QueueHandler, which delegates asynchronously
    queue_handler = QueueHandler(log_queue)
    root_logger.addHandler(queue_handler)
