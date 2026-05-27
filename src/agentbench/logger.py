"""Logging configuration for AgentBench."""

import logging
import sys


def setup_logger(name: str = "agentbench", level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger instance.

    Args:
        name: Logger name.
        level: Logging level.

    Returns:
        Configured logger.
    """
    _logger = logging.getLogger(name)

    if not _logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        _logger.addHandler(handler)
        _logger.setLevel(level)
        _logger.propagate = False

    return _logger


logger = setup_logger()
