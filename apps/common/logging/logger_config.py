"""MI Agent logging configuration using loguru.

Usage:
    from apps.common.logging.logger_config import logger

    logger.info("message")
    logger.debug("detailed info")
    logger.warning("warning message")
    logger.error("error message")
"""

from __future__ import annotations

import os
import sys

from loguru import logger

from apps.common.logging.console import format_console_record


# Remove default handler
logger.remove()


def setup_logging(log_level: str | None = None) -> None:
    """Configure loguru with the specified log level.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR).
                   If None, reads from settings or environment.

    """
    if log_level is None:
        # Try to get from settings, fallback to env var or default
        try:
            from apps.common.configs.config import get_settings

            log_level = get_settings().log_level.upper()
        except Exception:
            log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    else:
        log_level = log_level.upper()

    # Remove any existing handlers before adding new one
    logger.remove()

    # Single stdout handler with level filtering
    logger.add(
        sys.stdout,
        level=log_level,
        colorize=True,
        format=format_console_record,
    )


# Initialize logging immediately at module import
setup_logging()

__all__ = ["logger", "setup_logging"]
