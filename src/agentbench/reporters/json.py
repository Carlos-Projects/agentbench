"""JSON reporter for benchmark results."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agentbench.models import ScoreReport


class JSONReporter:
    """Generates JSON reports from benchmark results."""

    def generate(self, report: ScoreReport, indent: int = 2) -> str:
        """Generate a JSON string from a score report.

        Args:
            report: Score report to serialize.
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        data = self._report_to_dict(report)
        return json.dumps(data, indent=indent, default=str)

    def save(self, report: ScoreReport, filepath: str | Path) -> str:
        """Save a score report as a JSON file.

        Args:
            report: Score report to save.
            filepath: Output file path.

        Returns:
            Path to the saved file.
        """
        from agentbench.utils.security import safe_resolve_path

        path = safe_resolve_path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self._report_to_dict(report)
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def _report_to_dict(self, report: ScoreReport) -> dict[str, Any]:
        return {
            "agent_id": report.agent_id,
            "agent_version": report.agent_version,
            "timestamp": report.timestamp.isoformat() if isinstance(report.timestamp, datetime) else str(report.timestamp),
            "overall_score": report.overall_score,
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
            "duration_seconds": report.duration_seconds,
            "categories": [
                {
                    "name": c.name,
                    "score": c.score,
                    "weight": c.weight,
                    "tests_passed": c.tests_passed,
                    "tests_failed": c.tests_failed,
                    "tests_total": c.tests_total,
                }
                for c in report.categories
            ],
            "results": [
                {
                    "test_id": r.test_case.id,
                    "test_name": r.test_case.name,
                    "category": r.test_case.category,
                    "status": r.status.value,
                    "score": r.score,
                    "response_time_ms": r.response_time_ms,
                    "detected": r.detected,
                }
                for r in report.results
            ],
        }
