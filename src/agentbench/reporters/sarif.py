"""SARIF (Static Analysis Results Interchange Format) reporter.

Generates SARIF v2.1.0 output compatible with GitHub Code Scanning,
VS Code, and other SARIF consumers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentbench.models import ScoreReport, TestStatus


class SARIFReporter:
    """Generates SARIF v2.1.0 reports from benchmark results."""

    def generate(self, report: ScoreReport) -> dict[str, Any]:
        """Generate a SARIF v2.1.0 run object.

        Args:
            report: Score report from a benchmark run.

        Returns:
            SARIF-compatible dictionary.
        """
        tool_name = f"AgentBench ({report.agent_id})"
        rules: list[dict[str, Any]] = []
        results: list[dict[str, Any]] = []

        for i, cat in enumerate(report.categories):
            rule_id = f"AGENTBENCH-{cat.name.upper()}"
            rules.append(
                {
                    "id": rule_id,
                    "name": f"Security: {cat.name}",
                    "shortDescription": {"text": f"AgentBench benchmark category: {cat.name}"},
                    "fullDescription": {"text": f"Security benchmark results for {cat.name}. Score: {cat.score:.1f}/100. Tests: {cat.tests_passed}/{cat.tests_total} passed."},
                    "defaultConfiguration": {"level": self._sarif_level(cat.score)},
                    "properties": {"category": cat.name, "score": cat.score, "tests_passed": cat.tests_passed, "tests_total": cat.tests_total},
                }
            )

        for r in report.results:
            if r.status in (TestStatus.FAILED, TestStatus.ERROR):
                rule_id = f"AGENTBENCH-{r.test_case.category.upper()}"
                results.append(
                    {
                        "ruleId": rule_id,
                        "level": "error",
                        "message": {"text": f"{r.test_case.name}: {r.test_case.description}"},
                        "locations": [{"physicalLocation": {"artifactLocation": {"uri": r.test_case.target or "agent://target"}}}],
                        "properties": {
                            "test_id": r.test_case.id,
                            "prompt": r.test_case.prompt[:200],
                            "expected_behavior": r.test_case.expected_behavior,
                            "response": r.response[:200],
                            "response_time_ms": r.response_time_ms,
                            "error": r.error_message,
                        },
                    }
                )

        sarif: dict[str, Any] = {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": tool_name,
                            "version": "0.1.0",
                            "informationUri": "https://github.com/Carlos-Projects/agentbench",
                            "rules": rules,
                        }
                    },
                    "results": results,
                    "properties": {
                        "overall_score": report.overall_score,
                        "total_tests": report.total_tests,
                        "passed_tests": report.passed_tests,
                        "failed_tests": report.failed_tests,
                        "duration_seconds": report.duration_seconds,
                    },
                }
            ],
        }

        return sarif

    def save(self, report: ScoreReport, filepath: str | Path) -> str:
        """Save a SARIF report as a JSON file.

        Args:
            report: Score report from a benchmark run.
            filepath: Output SARIF file path.

        Returns:
            Path to the saved file.
        """
        from agentbench.utils.security import safe_resolve_path

        path = safe_resolve_path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        sarif = self.generate(report)
        path.write_text(json.dumps(sarif, indent=2, default=str))
        return str(path)

    @staticmethod
    def _sarif_level(score: float) -> str:
        if score < 50:
            return "error"
        if score < 75:
            return "warning"
        if score < 90:
            return "note"
        return "none"
