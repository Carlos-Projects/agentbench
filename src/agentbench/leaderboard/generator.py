"""Leaderboard generator for ranking benchmark results."""

from __future__ import annotations

from agentbench.models import LeaderboardEntry, ScoreReport


class LeaderboardGenerator:
    """Generates ranked leaderboards from score reports."""

    def generate(self, reports: list[ScoreReport]) -> list[LeaderboardEntry]:
        """Generate a leaderboard from score reports, sorted by overall score.

        Args:
            reports: List of score reports to rank.

        Returns:
            Ranked list of LeaderboardEntry objects.
        """
        entries: list[LeaderboardEntry] = []
        for report in reports:
            category_scores = {c.name: c.score for c in report.categories}
            entries.append(
                LeaderboardEntry(
                    agent_id=report.agent_id,
                    agent_version=report.agent_version,
                    overall_score=report.overall_score,
                    category_scores=category_scores,
                    total_tests=report.total_tests,
                    passed_tests=report.passed_tests,
                    timestamp=report.timestamp,
                    metadata=report.config,
                )
            )

        entries.sort(key=lambda e: e.overall_score, reverse=True)
        for i, entry in enumerate(entries, 1):
            entry.rank = i

        return entries

    def generate_by_category(
        self,
        reports: list[ScoreReport],
        category: str,
    ) -> list[LeaderboardEntry]:
        """Generate a leaderboard filtered by a specific category.

        Args:
            reports: List of score reports.
            category: Category name to filter by.

        Returns:
            Ranked list of LeaderboardEntry objects sorted by category score.
        """
        entries: list[LeaderboardEntry] = []
        for report in reports:
            cat_scores = {c.name: c.score for c in report.categories}
            if category not in cat_scores:
                continue
            entries.append(
                LeaderboardEntry(
                    agent_id=report.agent_id,
                    agent_version=report.agent_version,
                    overall_score=cat_scores.get(category, 0.0),
                    category_scores=cat_scores,
                    total_tests=report.total_tests,
                    passed_tests=report.passed_tests,
                    timestamp=report.timestamp,
                    metadata=report.config,
                )
            )

        entries.sort(key=lambda e: e.overall_score, reverse=True)
        for i, entry in enumerate(entries, 1):
            entry.rank = i

        return entries
