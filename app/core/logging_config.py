"""
Centralized logging configuration using loguru.

Every agent and service imports `logger` from here so log output is
consistent across the whole system (same format, same level control via
the LOG_LEVEL env var). This also makes it trivial to redirect logs to a
file or a log-aggregation service later without touching business logic.
"""

import sys

from loguru import logger

from app.core.config import get_settings

settings = get_settings()

# Remove the default handler so we control format/level precisely.
logger.remove()

logger.add(
    sys.stdout,
    level=settings.log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# Also persist logs to a rotating file for later debugging / audit trail.
logger.add(
    "data/reports/app.log",
    level=settings.log_level,
    rotation="5 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
)

__all__ = ["logger"]
