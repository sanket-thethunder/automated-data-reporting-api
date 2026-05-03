"""
Logging configuration.

Provides a consistent, structured logger across the entire application.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger configured with a sensible default format.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
