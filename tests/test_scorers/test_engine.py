"""Tests for ScoreEngine."""

from agentbench.models import BenchmarkResult, BenchmarkTestCase, TestStatus
from agentbench.scorers.engine import ScoreEngine
from agentbench.scorers.normalizer import ScoreNormalizer


class TestScoreEngine:
    def setup_method(self) -> None:
        self.engine = ScoreEngine()

    def _make_result(self, category: str, status: TestStatus, weight: float = 1.0) -> BenchmarkResult:
        from agentbench.models import Severity as _Sev

        sev = _Sev.CRITICAL if status == TestStatus.FAILED else _Sev.MEDIUM
        tc = BenchmarkTestCase(
            id=f"t-{category}-{status.value}",
            name=f"Test {category}",
            category=category,
            weight=weight,
            severity=sev,
        )
        score = 100.0 if status == TestStatus.PASSED else 0.0
        return BenchmarkResult(test_case=tc, status=status, score=score)

    def test_compute_scores_empty_results(self) -> None:
        report = self.engine.compute_scores("agent-1", [])
        assert report.overall_score == 0.0
        assert report.total_tests == 0
        assert report.agent_id == "agent-1"

    def test_compute_scores_all_passed(self) -> None:
        results = [self._make_result("injection", TestStatus.PASSED) for _ in range(5)]
        report = self.engine.compute_scores("agent-1", results)
        assert report.overall_score == 100.0
        assert report.passed_tests == 5

    def test_compute_scores_all_failed(self) -> None:
        results = [self._make_result("injection", TestStatus.FAILED) for _ in range(3)]
        report = self.engine.compute_scores("agent-1", results)
        assert report.overall_score == 0.0
        assert report.failed_tests == 3

    def test_compute_scores_multiple_categories(self) -> None:
        results = [
            self._make_result("injection", TestStatus.PASSED),
            self._make_result("injection", TestStatus.FAILED),
            self._make_result("ssrf", TestStatus.PASSED),
            self._make_result("ssrf", TestStatus.PASSED),
        ]
        report = self.engine.compute_scores("agent-1", results)
        assert len(report.categories) == 2
        assert report.total_tests == 4

    def test_compute_scores_with_version(self) -> None:
        results = [self._make_result("test", TestStatus.PASSED)]
        report = self.engine.compute_scores("agent-1", results, agent_version="1.0.0")
        assert report.agent_version == "1.0.0"

    def test_compute_scores_with_config(self) -> None:
        results = [self._make_result("test", TestStatus.PASSED)]
        report = self.engine.compute_scores("agent-1", results, config={"target": "http://test"})
        assert report.config["target"] == "http://test"

    def test_group_by_category(self) -> None:
        results = [
            self._make_result("a", TestStatus.PASSED),
            self._make_result("a", TestStatus.FAILED),
            self._make_result("b", TestStatus.PASSED),
        ]
        grouped = self.engine._group_by_category(results)
        assert len(grouped) == 2
        assert len(grouped["a"]) == 2
        assert len(grouped["b"]) == 1

    def test_average_weight(self) -> None:
        results = [
            self._make_result("test", TestStatus.PASSED, weight=1.0),
            self._make_result("test", TestStatus.PASSED, weight=3.0),
        ]
        avg = ScoreEngine._get_average_weight(results)
        assert avg == 2.0

    def test_average_weight_empty(self) -> None:
        assert ScoreEngine._get_average_weight([]) == 1.0

    def test_custom_normalizer(self) -> None:
        normalizer = ScoreNormalizer()
        normalizer.register_category("test", scale=0.5)
        engine = ScoreEngine(normalizer=normalizer)
        results = [self._make_result("test", TestStatus.PASSED)]
        report = engine.compute_scores("agent-1", results)
        assert report.categories[0].score == 50.0
