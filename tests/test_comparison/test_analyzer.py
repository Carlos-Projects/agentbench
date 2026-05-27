"""Tests for ComparisonAnalyzer."""

from agentbench.comparison.analyzer import ComparisonAnalyzer
from agentbench.models import ScoreCategory, ScoreReport


class TestComparisonAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = ComparisonAnalyzer()

    def _make_report(self, agent_id: str, scores: dict[str, float]) -> ScoreReport:
        categories = [ScoreCategory(name=name, score=score, tests_total=1, tests_passed=int(score > 50)) for name, score in scores.items()]
        overall = sum(scores.values()) / len(scores) if scores else 0.0
        return ScoreReport(agent_id=agent_id, categories=categories, overall_score=overall, total_tests=len(scores))

    def test_compare_improvement(self) -> None:
        baseline = self._make_report("v1", {"injection": 70.0, "ssrf": 80.0})
        target = self._make_report("v2", {"injection": 85.0, "ssrf": 90.0})
        result = self.analyzer.compare(baseline, target)
        assert result.score_delta > 0
        assert result.baseline_id == "v1"
        assert result.target_id == "v2"

    def test_compare_regression(self) -> None:
        baseline = self._make_report("v1", {"injection": 90.0, "ssrf": 85.0})
        target = self._make_report("v2", {"injection": 60.0, "ssrf": 70.0})
        result = self.analyzer.compare(baseline, target)
        assert result.score_delta < 0
        assert result.regression_count > 0

    def test_compare_identical(self) -> None:
        baseline = self._make_report("v1", {"injection": 80.0})
        target = self._make_report("v2", {"injection": 80.0})
        result = self.analyzer.compare(baseline, target)
        assert result.score_delta == 0.0

    def test_category_deltas(self) -> None:
        baseline = self._make_report("v1", {"a": 50.0, "b": 80.0})
        target = self._make_report("v2", {"a": 70.0, "b": 60.0})
        result = self.analyzer.compare(baseline, target)
        assert result.category_deltas["a"] == 20.0
        assert result.category_deltas["b"] == -20.0

    def test_new_category_in_target(self) -> None:
        baseline = self._make_report("v1", {"a": 80.0})
        target = self._make_report("v2", {"a": 80.0, "b": 90.0})
        result = self.analyzer.compare(baseline, target)
        assert "b" in result.category_deltas

    def test_batch_compare(self) -> None:
        baseline = self._make_report("v1", {"a": 80.0})
        targets = [
            self._make_report("v2", {"a": 85.0}),
            self._make_report("v3", {"a": 75.0}),
        ]
        results = self.analyzer.batch_compare(baseline, targets)
        assert len(results) == 2
        assert results[0].score_delta > 0
        assert results[1].score_delta < 0

    def test_find_regressions(self) -> None:
        baseline = self._make_report("v1", {"a": 90.0, "b": 80.0})
        target = self._make_report("v2", {"a": 50.0, "b": 75.0})
        regressions = self.analyzer.find_regressions(baseline, target, threshold=-5.0)
        assert len(regressions) == 2
        assert ("a", -40.0) in regressions
        assert ("b", -5.0) in regressions
