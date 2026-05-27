"""Tests for ScoreDiff."""

from agentbench.comparison.diff import ScoreDiff
from agentbench.models import ScoreCategory, ScoreReport


class TestScoreDiff:
    def _make_report(
        self, agent_id: str, overall: float, categories: dict[str, float]
    ) -> ScoreReport:
        cats = [
            ScoreCategory(name=name, score=score, tests_total=1, tests_passed=int(score > 50))
            for name, score in categories.items()
        ]
        return ScoreReport(
            agent_id=agent_id, categories=cats, overall_score=overall, total_tests=len(cats)
        )

    def test_compute(self) -> None:
        baseline = self._make_report("v1", 80.0, {"a": 80.0})
        target = self._make_report("v2", 90.0, {"a": 90.0})
        diff = ScoreDiff.compute(baseline, target)
        assert diff.overall_delta == 10.0
        assert diff.category_deltas["a"] == 10.0

    def test_has_regression(self) -> None:
        baseline = self._make_report("v1", 90.0, {"a": 90.0})
        target = self._make_report("v2", 70.0, {"a": 70.0})
        diff = ScoreDiff.compute(baseline, target)
        assert diff.has_regression(threshold=-5.0)

    def test_no_regression(self) -> None:
        baseline = self._make_report("v1", 80.0, {"a": 80.0})
        target = self._make_report("v2", 85.0, {"a": 85.0})
        diff = ScoreDiff.compute(baseline, target)
        assert not diff.has_regression()

    def test_regressed_categories(self) -> None:
        baseline = self._make_report("v1", 80.0, {"a": 80.0, "b": 80.0})
        target = self._make_report("v2", 0.0, {"a": 60.0, "b": 40.0})
        diff = ScoreDiff.compute(baseline, target)
        regressed = diff.regressed_categories(threshold=-5.0)
        assert "b" in regressed

    def test_improved_categories(self) -> None:
        baseline = self._make_report("v1", 50.0, {"a": 50.0})
        target = self._make_report("v2", 90.0, {"a": 90.0})
        diff = ScoreDiff.compute(baseline, target)
        improved = diff.improved_categories(threshold=5.0)
        assert "a" in improved
