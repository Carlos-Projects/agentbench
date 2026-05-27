"""Tests for leaderboard modules."""

import json
from pathlib import Path

from agentbench.leaderboard.api import LeaderboardAPI
from agentbench.leaderboard.generator import LeaderboardGenerator
from agentbench.leaderboard.publisher import LeaderboardPublisher
from agentbench.models import ScoreCategory, ScoreReport


class TestLeaderboardGenerator:
    def setup_method(self) -> None:
        self.generator = LeaderboardGenerator()

    def _make_report(self, agent_id: str, score: float) -> ScoreReport:
        cats = [
            ScoreCategory(name="test", score=score, tests_total=1, tests_passed=int(score > 50))
        ]
        return ScoreReport(
            agent_id=agent_id,
            categories=cats,
            overall_score=score,
            total_tests=1,
            passed_tests=int(score > 50),
        )

    def test_generate_empty(self) -> None:
        entries = self.generator.generate([])
        assert entries == []

    def test_generate_single(self) -> None:
        entries = self.generator.generate([self._make_report("agent-1", 85.0)])
        assert len(entries) == 1
        assert entries[0].rank == 1

    def test_generate_multiple(self) -> None:
        reports = [
            self._make_report("agent-1", 90.0),
            self._make_report("agent-2", 70.0),
            self._make_report("agent-3", 80.0),
        ]
        entries = self.generator.generate(reports)
        assert entries[0].rank == 1
        assert entries[0].agent_id == "agent-1"
        assert entries[2].rank == 3
        assert entries[2].agent_id == "agent-2"

    def test_generate_by_category(self) -> None:
        reports = [
            self._make_report("agent-1", 90.0),
            self._make_report("agent-2", 70.0),
        ]
        entries = self.generator.generate_by_category(reports, "test")
        assert len(entries) == 2
        assert entries[0].agent_id == "agent-1"

    def test_generate_by_category_missing(self) -> None:
        report = ScoreReport(agent_id="agent-1", total_tests=0)
        entries = self.generator.generate_by_category([report], "nonexistent")
        assert entries == []


class TestLeaderboardAPI:
    def setup_method(self) -> None:
        self.api = LeaderboardAPI()

    def _make_report(self, agent_id: str, score: float) -> ScoreReport:
        cats = [
            ScoreCategory(name="test", score=score, tests_total=1, tests_passed=int(score > 50))
        ]
        return ScoreReport(agent_id=agent_id, categories=cats, overall_score=score, total_tests=1)

    def test_load_and_get_top(self) -> None:
        reports = [self._make_report(f"agent-{i}", float(100 - i * 10)) for i in range(5)]
        self.api.load(reports)
        top = self.api.get_top(3)
        assert len(top) == 3
        assert top[0].rank == 1

    def test_get_by_agent(self) -> None:
        reports = [self._make_report("agent-1", 85.0), self._make_report("agent-2", 75.0)]
        self.api.load(reports)
        entries = self.api.get_by_agent("agent-1")
        assert len(entries) == 1

    def test_get_by_rank_range(self) -> None:
        reports = [self._make_report(f"agent-{i}", float(100 - i)) for i in range(10)]
        self.api.load(reports)
        entries = self.api.get_by_rank_range(1, 3)
        assert len(entries) == 3

    def test_search(self) -> None:
        reports = [self._make_report("alpha-agent", 90.0), self._make_report("beta-agent", 80.0)]
        self.api.load(reports)
        results = self.api.search("alpha")
        assert len(results) == 1

    def test_search_empty(self) -> None:
        reports = [self._make_report("agent-1", 85.0)]
        self.api.load(reports)
        results = self.api.search("nonexistent")
        assert results == []


class TestLeaderboardPublisher:
    def setup_method(self) -> None:
        self.publisher = LeaderboardPublisher(output_dir="/tmp/agentbench_test_lb")

    def _make_report(self, agent_id: str, score: float) -> ScoreReport:
        cats = [
            ScoreCategory(name="test", score=score, tests_total=1, tests_passed=int(score > 50))
        ]
        return ScoreReport(agent_id=agent_id, categories=cats, overall_score=score, total_tests=1)

    def test_publish_json(self) -> None:
        reports = [self._make_report("agent-1", 85.0)]
        path = self.publisher.publish_json(reports, "test_lb.json")
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert len(data) == 1
        assert data[0]["agent_id"] == "agent-1"

    def test_publish_category_json(self) -> None:
        reports = [self._make_report("agent-1", 85.0)]
        path = self.publisher.publish_category_json(reports, "test", "test_cat.json")
        assert Path(path).exists()

    def test_publish_markdown(self) -> None:
        reports = [self._make_report("agent-1", 85.0)]
        path = self.publisher.publish_markdown(reports, "test_lb.md")
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "agent-1" in content
