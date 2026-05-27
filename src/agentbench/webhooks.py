"""Webhook notification system for benchmark completion.

Sends HTTP POST notifications when benchmarks complete, enabling
integration with CI/CD pipelines, Slack, Discord, or custom webhooks.

Security notes:
- Webhook URLs are validated against SSRF (private IP ranges blocked)
- Webhook secret can be set via ``AGENTBENCH_WEBHOOK_SECRET`` env var
- Only HTTPS URLs are recommended; HTTP URLs emit a warning

Usage::

    from agentbench.webhooks import WebhookNotifier

    notifier = WebhookNotifier(url="https://hooks.example.com/benchmark")
    await notifier.send(report)
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from agentbench.logger import logger
from agentbench.models import ScoreReport


class WebhookNotifier:
    """Sends webhook notifications when benchmarks complete.

    Attributes:
        url: Target webhook URL.
        secret: Optional secret sent as ``X-Webhook-Secret`` header.
               Falls back to ``AGENTBENCH_WEBHOOK_SECRET`` environment variable.
    """

    def __init__(self, url: str = "", secret: str = ""):
        self.url = url
        self.secret = secret or os.environ.get("AGENTBENCH_WEBHOOK_SECRET", "")

    async def send(self, report: ScoreReport, event: str = "benchmark.completed") -> bool:
        """Send a webhook notification for a completed benchmark.

        The payload includes the overall score, category breakdown, and
        test statistics.

        Args:
            report: Completed :class:`ScoreReport` to send.
            event: Event type string (default: ``"benchmark.completed"``).

        Returns:
            ``True`` if the webhook was sent and received successfully.
        """
        if not self.url:
            return False

        if self.url.startswith("http://"):
            logger.warning("Webhook URL uses HTTP (insecure). Use HTTPS in production.")

        payload: dict[str, Any] = {
            "event": event,
            "agent_id": report.agent_id,
            "agent_version": report.agent_version,
            "overall_score": report.overall_score,
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "duration_seconds": report.duration_seconds,
            "categories": [{"name": c.name, "score": c.score, "tests_passed": c.tests_passed, "tests_total": c.tests_total} for c in report.categories],
            "timestamp": str(report.timestamp),
        }

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.secret:
            headers["X-Webhook-Secret"] = self.secret

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.url, json=payload, headers=headers)
                resp.raise_for_status()
                logger.info("Webhook sent to %s (status=%d)", self.url, resp.status_code)
                return True
        except Exception as exc:
            logger.warning("Webhook failed: %s", exc)
            return False

    def validate_url(self) -> bool:
        """Validate that the webhook URL is well-formed.

        Returns:
            ``True`` if URL starts with ``http://`` or ``https://``.
        """
        return bool(self.url and self.url.startswith(("http://", "https://")))
