"""Retry utilities for HTTP requests."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from agentbench.logger import logger


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs: Any,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry.
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay between retries in seconds.
        backoff: Multiplier for exponential backoff.
        *args: Positional arguments for func.
        **kwargs: Keyword arguments for func.

    Returns:
        Result from func.

    Raises:
        Last exception raised by func after all retries exhausted.
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                delay = base_delay * (backoff ** (attempt - 1))
                logger.warning(
                    "Retry %d/%d for %s after error: %s (waiting %.1fs)",
                    attempt,
                    max_retries,
                    func.__name__,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

    msg = f"All {max_retries} retries failed for {func.__name__}"
    logger.error(msg)
    if last_exc:
        raise last_exc
    raise RuntimeError(msg)
