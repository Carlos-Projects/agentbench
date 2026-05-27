"""Tests for MetricsCalculator."""

import pytest

from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    Severity,
    TestStatus,
)
from agentbench.scorers.metrics import MetricsCalculator


class TestMetricsCalculator:
    def setup_method(self) -> None:
        self.calc = MetricsCalculator()

    def _make_result(self, status: TestStatus, score: float | None = None, weight: float = 1.0, severity: Severity | None = None) -> BenchmarkResult:
        if score is None:
            score = 100.0 if status == TestStatus.PASSED else 0.0
        sev = severity or (Severity.CRITICAL if status == TestStatus.FAILED else Severity.MEDIUM)
        tc = BenchmarkTestCase(id=f"t-{status.value}", name="Test", category="test", weight=weight, severity=sev)
        return BenchmarkResult(test_case=tc, status=status, score=score)

    def test_empty_results_returns_zero(self) -> None:
        assert self.calc.calculate_category_score([]) == 0.0

    def test_all_passed(self) -> None:
        results = [self._make_result(TestStatus.PASSED) for _ in range(3)]
        score = self.calc.calculate_category_score(results)
        assert score == 100.0

    def test_all_failed(self) -> None:
        results = [self._make_result(TestStatus.FAILED) for _ in range(3)]
        score = self.calc.calculate_category_score(results)
        assert score == 0.0

    def test_mixed_results(self) -> None:
        results = [
            self._make_result(TestStatus.PASSED, weight=1.0),
            self._make_result(TestStatus.FAILED, weight=1.0),
            self._make_result(TestStatus.PASSED, weight=1.0),
        ]
        score = self.calc.calculate_category_score(results)
        assert 60.0 < score < 70.0

    def test_weighted_scores(self) -> None:
        results = [
            self._make_result(TestStatus.PASSED, weight=2.0),
            self._make_result(TestStatus.FAILED, weight=1.0),
        ]
        score = self.calc.calculate_category_score(results)
        expected = (2.0 * 100.0) / 3.0
        assert score == pytest.approx(expected, rel=0.1)

    def test_skipped_contributes_half(self) -> None:
        results = [self._make_result(TestStatus.SKIPPED)]
        score = self.calc.calculate_category_score(results)
        assert score == 50.0

    def test_overall_empty_categories(self) -> None:
        assert self.calc.calculate_overall([]) == 0.0

    def test_overall_single_category(self) -> None:
        cats = [ScoreCategory(name="test", score=85.0, weight=1.0)]
        assert self.calc.calculate_overall(cats) == 85.0

    def test_overall_weighted_categories(self) -> None:
        cats = [
            ScoreCategory(name="a", score=100.0, weight=2.0),
            ScoreCategory(name="b", score=50.0, weight=1.0),
        ]
        overall = self.calc.calculate_overall(cats)
        expected = (100.0 * 2.0 + 50.0 * 1.0) / 3.0
        assert overall == pytest.approx(expected)

    def test_pass_rate(self) -> None:
        report = ScoreReport(agent_id="test", total_tests=10, passed_tests=7)
        assert self.calc.pass_rate(report) == 70.0

    def test_pass_rate_zero_tests(self) -> None:
        report = ScoreReport(agent_id="test")
        assert self.calc.pass_rate(report) == 0.0

    def test_failure_rate(self) -> None:
        report = ScoreReport(agent_id="test", total_tests=10, failed_tests=3)
        assert self.calc.failure_rate(report) == 30.0

    def test_category_pass_rate(self) -> None:
        results = [
            self._make_result(TestStatus.PASSED),
            self._make_result(TestStatus.FAILED),
            self._make_result(TestStatus.PASSED),
        ]
        assert self.calc.category_pass_rate(results) == pytest.approx(66.666, rel=0.1)

    def test_category_pass_rate_empty(self) -> None:
        assert self.calc.category_pass_rate([]) == 0.0
