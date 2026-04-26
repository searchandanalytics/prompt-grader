"""Structured logging setup for PromptGrade."""

import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure root logger with a simple timestamped format.

    Args:
        level: Logging level string (e.g. "INFO", "DEBUG").
    """
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )
