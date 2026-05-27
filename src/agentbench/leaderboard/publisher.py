"""Publisher for leaderboard results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentbench.leaderboard.generator import LeaderboardGenerator
from agentbench.models import ScoreReport


class LeaderboardPublisher:
    """Publishes leaderboard results to files or streams."""

    def __init__(self, output_dir: str = "leaderboard"):
        self.output_dir = Path(output_dir)
        self.generator = LeaderboardGenerator()

    def publish_json(
        self,
        reports: list[ScoreReport],
        filename: str = "leaderboard.json",
    ) -> str:
        """Publish leaderboard as JSON file.

        Args:
            reports: List of score reports.
            filename: Output filename.

        Returns:
            Path to the published file.
        """
        entries = self.generator.generate(reports)
        data = [e.model_dump() for e in entries]
        return self._write_json(data, filename)

    def publish_category_json(
        self,
        reports: list[ScoreReport],
        category: str,
        filename: str = "",
    ) -> str:
        """Publish per-category leaderboard as JSON.

        Args:
            reports: List of score reports.
            category: Category name.
            filename: Output filename.

        Returns:
            Path to the published file.
        """
        entries = self.generator.generate_by_category(reports, category)
        data = [e.model_dump() for e in entries]
        filename = filename or f"leaderboard_{category}.json"
        return self._write_json(data, filename)

    def publish_markdown(
        self,
        reports: list[ScoreReport],
        filename: str = "LEADERBOARD.md",
    ) -> str:
        """Publish leaderboard as Markdown table.

        Args:
            reports: List of score reports.
            filename: Output filename.

        Returns:
            Path to the published file.
        """
        entries = self.generator.generate(reports)
        lines = [
            "# AgentBench Security Leaderboard\n",
            "| Rank | Agent | Version | Overall Score | Tests Passed | Total Tests |",
            "|------|-------|---------|--------------|--------------|-------------|",
        ]
        for e in entries:
            lines.append(
                f"| {e.rank} | {e.agent_id} | {e.agent_version} | {e.overall_score:.1f} | {e.passed_tests} | {e.total_tests} |"
            )

        return self._write_text("\n".join(lines), filename)

    def _write_json(self, data: list[dict[str, Any]], filename: str) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(json.dumps(data, indent=2, default=str))
        return str(path)

    def _write_text(self, content: str, filename: str) -> str:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / filename
        path.write_text(content)
        return str(path)
