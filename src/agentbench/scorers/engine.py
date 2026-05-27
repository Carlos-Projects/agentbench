"""Core scoring engine for benchmark results."""

from __future__ import annotations

from typing import Any

from agentbench.models import (
    BenchmarkResult,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)
from agentbench.scorers.metrics import MetricsCalculator
from agentbench.scorers.normalizer import ScoreNormalizer


class ScoreEngine:
    """Engine that computes scores from benchmark execution results."""

    def __init__(
        self,
        normalizer: ScoreNormalizer | None = None,
        calculator: MetricsCalculator | None = None,
    ):
        self.normalizer = normalizer or ScoreNormalizer()
        self.calculator = calculator or MetricsCalculator()

    def compute_scores(
        self,
        agent_id: str,
        results: list[BenchmarkResult],
        agent_version: str = "",
        config: dict[str, Any] | None = None,
    ) -> ScoreReport:
        """Compute a complete ScoreReport from benchmark results.

        Args:
            agent_id: Identifier for the agent being tested.
            results: List of benchmark execution results.
            agent_version: Version string for the agent.
            config: Optional configuration metadata.

        Returns:
            Complete ScoreReport with per-category and overall scores.
        """
        categories = self._group_by_category(results)
        category_scores: list[ScoreCategory] = []

        for category_name, category_results in sorted(categories.items()):
            score = self.calculator.calculate_category_score(category_results)
            tests_passed = sum(1 for r in category_results if r.status == TestStatus.PASSED)
            tests_failed = sum(
                1 for r in category_results if r.status in (TestStatus.FAILED, TestStatus.ERROR)
            )
            category_weight = self._get_average_weight(category_results)

            normalized_score = self.normalizer.normalize(score, category_name)

            category_scores.append(
                ScoreCategory(
                    name=category_name,
                    score=normalized_score,
                    weight=category_weight,
                    tests_passed=tests_passed,
                    tests_failed=tests_failed,
                    tests_total=len(category_results),
                    details={"raw_score": score, "num_results": len(category_results)},
                )
            )

        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if r.status in (TestStatus.FAILED, TestStatus.ERROR))

        overall_score = self.calculator.calculate_overall(category_scores)

        return ScoreReport(
            agent_id=agent_id,
            agent_version=agent_version,
            categories=category_scores,
            overall_score=overall_score,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            config=config or {},
            results=results,
        )

    def _group_by_category(
        self, results: list[BenchmarkResult]
    ) -> dict[str, list[BenchmarkResult]]:
        categories: dict[str, list[BenchmarkResult]] = {}
        for r in results:
            cat = r.test_case.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)
        return categories

    @staticmethod
    def _get_average_weight(results: list[BenchmarkResult]) -> float:
        if not results:
            return 1.0
        return sum(r.test_case.weight for r in results) / len(results)
