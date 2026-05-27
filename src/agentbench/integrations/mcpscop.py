"""MCPscop-compatible report generation from AgentBench results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from agentbench.models import ScoreReport, TestStatus

CATEGORY_SEVERITY_MAP = {
    "prompt_injection": "critical",
    "tool_poisoning": "critical",
    "ssrf": "high",
    "jailbreak": "critical",
    "data_exfiltration": "high",
    "memory_attacks": "medium",
    "multi_agent": "high",
}


class MCPscopExporter:
    """Exports benchmark results in MCPscop-compatible format.

    Generates SecurityEvent and Finding payloads that can be ingested
    by MCPscop's ``/api/events`` and import endpoints.
    """

    def to_security_events(self, report: ScoreReport) -> list[dict]:
        """Convert benchmark results to MCPscop SecurityEvent list.

        Args:
            report: Score report from a benchmark run.

        Returns:
            List of MCPscop-compatible SecurityEvent dicts.
        """
        events: list[dict] = []
        for r in report.results:
            if r.status in (TestStatus.FAILED, TestStatus.ERROR):
                events.append(
                    {
                        "event_type": r.test_case.category,
                        "severity": CATEGORY_SEVERITY_MAP.get(r.test_case.category, "medium"),
                        "message": f"Benchmark failed: {r.test_case.name}",
                        "source": "agentbench",
                        "tool": r.test_case.id,
                        "details": {
                            "test_id": r.test_case.id,
                            "test_name": r.test_case.name,
                            "prompt": r.test_case.prompt[:200],
                            "expected_behavior": r.test_case.expected_behavior,
                            "response": r.response[:500],
                            "response_time_ms": r.response_time_ms,
                            "error": r.error_message,
                        },
                        "blocked": True,
                        "created_at": datetime.now().isoformat(),
                    }
                )
        return events

    def to_findings(self, report: ScoreReport, scan_id: str = "") -> list[dict]:
        """Convert benchmark results to MCPscop Finding list.

        Args:
            report: Score report from a benchmark run.
            scan_id: Optional scan identifier.

        Returns:
            List of MCPscop-compatible Finding dicts.
        """
        findings: list[dict] = []
        for cat in report.categories:
            findings.append(
                {
                    "scan_id": scan_id or f"agentbench-{report.agent_id}-{datetime.now().isoformat()}",
                    "scanner": "agentbench",
                    "tool_name": cat.name,
                    "severity": CATEGORY_SEVERITY_MAP.get(cat.name, "medium"),
                    "title": f"AgentBench {cat.name} score: {cat.score:.1f}/100",
                    "description": f"{cat.tests_passed}/{cat.tests_total} tests passed",
                    "recommendation": self._recommendation(cat.score),
                    "raw_data": cat.model_dump(),
                }
            )
        return findings

    def save_events_json(self, report: ScoreReport, filepath: str | Path) -> str:
        """Save as MCPscop events JSON file.

        Args:
            report: Score report from a benchmark run.
            filepath: Output JSON file path.

        Returns:
            Path to the saved file.
        """
        import json

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        events = self.to_security_events(report)
        path.write_text(json.dumps(events, indent=2, default=str))
        return str(path)

    def save_findings_json(self, report: ScoreReport, filepath: str | Path) -> str:
        """Save as MCPscop findings JSON file.

        Args:
            report: Score report from a benchmark run.
            filepath: Output JSON file path.

        Returns:
            Path to the saved file.
        """
        import json

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        findings = self.to_findings(report)
        path.write_text(json.dumps(findings, indent=2, default=str))
        return str(path)

    @staticmethod
    def _recommendation(score: float) -> str:
        if score >= 90:
            return "No action needed"
        if score >= 70:
            return "Review failed tests and consider policy updates"
        if score >= 50:
            return "Implement blocking rules for vulnerable categories"
        return "Urgent: deploy MCPGuard with strict policies"
