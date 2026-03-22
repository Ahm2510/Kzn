# utils/logger.py

import logging
import sys
from typing import Optional

from app.config.settings import settings

_LOGGING_CONFIGURED = False


def configure_logging(level: Optional[str] = None) -> None:
    """
    Configure application-wide logging.

    Safe to call multiple times.
    """
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    log_level = (level or settings.LOG_LEVEL).upper()
    log_format = settings.LOG_FORMAT.lower()

    if log_format == "json":
        formatter = logging.Formatter(
            fmt='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)

    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger.
    """
    configure_logging()
    return logging.getLogger(name)
