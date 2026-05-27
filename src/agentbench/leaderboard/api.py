"""Simple API for querying leaderboard data."""

from __future__ import annotations

from agentbench.leaderboard.generator import LeaderboardGenerator
from agentbench.models import LeaderboardEntry, ScoreReport


class LeaderboardAPI:
    """API for querying and filtering leaderboard data."""

    def __init__(self) -> None:
        self.generator = LeaderboardGenerator()
        self._entries: list[LeaderboardEntry] = []

    def load(self, reports: list[ScoreReport]) -> None:
        """Load score reports into the API.

        Args:
            reports: List of score reports.
        """
        self._entries = self.generator.generate(reports)

    def get_top(self, n: int = 10) -> list[LeaderboardEntry]:
        """Get top N entries from the leaderboard.

        Args:
            n: Number of top entries to return.

        Returns:
            List of top N entries.
        """
        return self._entries[:n]

    def get_by_agent(self, agent_id: str) -> list[LeaderboardEntry]:
        """Get leaderboard entries for a specific agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            List of entries matching the agent ID.
        """
        return [e for e in self._entries if e.agent_id == agent_id]

    def get_by_rank_range(self, start: int, end: int) -> list[LeaderboardEntry]:
        """Get entries within a rank range.

        Args:
            start: Start rank (inclusive).
            end: End rank (inclusive).

        Returns:
            List of entries in the rank range.
        """
        return [e for e in self._entries if start <= e.rank <= end]

    def search(self, query: str) -> list[LeaderboardEntry]:
        """Search leaderboard entries by agent ID or version.

        Args:
            query: Search string.

        Returns:
            List of matching entries.
        """
        query_lower = query.lower()
        return [
            e
            for e in self._entries
            if query_lower in e.agent_id.lower() or query_lower in e.agent_version.lower()
        ]
