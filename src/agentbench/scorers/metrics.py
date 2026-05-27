"""Metrics calculation utilities for benchmark scoring."""

from __future__ import annotations

from agentbench.models import BenchmarkResult, ScoreCategory, ScoreReport, TestStatus

SEVERITY_PENALTY = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
    "info": 0.0,
}


class MetricsCalculator:
    """Calculates scoring metrics from benchmark results.

    Supports severity-weighted scoring: critical failures penalize more
    than low-severity failures.
    """

    def __init__(self, use_severity_weighting: bool = True):
        self.use_severity_weighting = use_severity_weighting

    def calculate_category_score(self, results: list[BenchmarkResult]) -> float:
        """Calculate raw score for a category (0.0 to 100.0).

        Uses weighted average: each passed test contributes its weight
        to the score. Failed/error tests contribute 0.

        Args:
            results: Benchmark results for a single category.

        Returns:
            Raw category score between 0 and 100.
        """
        if not results:
            return 0.0

        total_weight = sum(r.test_case.weight for r in results)
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for r in results:
            if r.status == TestStatus.PASSED:
                weighted_sum += r.test_case.weight * r.score
            elif r.status == TestStatus.FAILED and self.use_severity_weighting:
                penalty = SEVERITY_PENALTY.get(r.test_case.severity.value, 0.5)
                weighted_sum += r.test_case.weight * 100.0 * (1.0 - penalty)
            elif r.status == TestStatus.SKIPPED:
                weighted_sum += r.test_case.weight * 50.0

        raw_score = weighted_sum / total_weight
        return max(0.0, min(100.0, raw_score))

    def calculate_overall(self, categories: list[ScoreCategory]) -> float:
        """Calculate overall score across categories using weighted average.

        Args:
            categories: List of category scores with weights.

        Returns:
            Overall score between 0 and 100.
        """
        if not categories:
            return 0.0

        total_weight = sum(c.weight for c in categories)
        if total_weight == 0:
            return 0.0

        weighted_sum = sum(c.score * c.weight for c in categories)
        overall = weighted_sum / total_weight
        return max(0.0, min(100.0, overall))

    def pass_rate(self, report: ScoreReport) -> float:
        """Calculate pass rate as percentage.

        Args:
            report: Score report to evaluate.

        Returns:
            Pass rate between 0 and 100.
        """
        if report.total_tests == 0:
            return 0.0
        return (report.passed_tests / report.total_tests) * 100.0

    def failure_rate(self, report: ScoreReport) -> float:
        """Calculate failure rate as percentage.

        Args:
            report: Score report to evaluate.

        Returns:
            Failure rate between 0 and 100.
        """
        if report.total_tests == 0:
            return 0.0
        return (report.failed_tests / report.total_tests) * 100.0

    def category_pass_rate(self, results: list[BenchmarkResult]) -> float:
        """Calculate pass rate for a specific category.

        Args:
            results: Results for a single category.

        Returns:
            Pass rate between 0 and 100.
        """
        if not results:
            return 0.0
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        return (passed / len(results)) * 100.0
