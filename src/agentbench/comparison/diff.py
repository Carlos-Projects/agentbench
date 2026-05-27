"""Score difference tracking utilities."""

from __future__ import annotations

from dataclasses import dataclass, field

from agentbench.models import ScoreReport


@dataclass
class ScoreDiff:
    """Tracks differences between two score reports."""

    baseline: ScoreReport
    target: ScoreReport
    overall_delta: float = 0.0
    category_deltas: dict[str, float] = field(default_factory=dict)
    test_deltas: dict[str, tuple[float, float]] = field(default_factory=dict)

    @classmethod
    def compute(cls, baseline: ScoreReport, target: ScoreReport) -> ScoreDiff:
        """Compute differences between baseline and target reports.

        Args:
            baseline: Baseline score report.
            target: Target score report.

        Returns:
            ScoreDiff with computed deltas.
        """
        overall_delta = round(target.overall_score - baseline.overall_score, 2)

        category_deltas: dict[str, float] = {}
        baseline_cats = {c.name: c.score for c in baseline.categories}
        target_cats = {c.name: c.score for c in target.categories}
        for cat in set(baseline_cats) | set(target_cats):
            b = baseline_cats.get(cat, 0.0)
            t = target_cats.get(cat, 0.0)
            category_deltas[cat] = round(t - b, 2)

        test_deltas: dict[str, tuple[float, float]] = {}
        baseline_results = {r.test_case.id: r.score for r in baseline.results}
        target_results = {r.test_case.id: r.score for r in target.results}
        for test_id in set(baseline_results) | set(target_results):
            b = baseline_results.get(test_id, 0.0)
            t = target_results.get(test_id, 0.0)
            test_deltas[test_id] = (b, t)

        return cls(
            baseline=baseline,
            target=target,
            overall_delta=overall_delta,
            category_deltas=category_deltas,
            test_deltas=test_deltas,
        )

    def has_regression(self, threshold: float = -5.0) -> bool:
        """Check if there is a significant regression.

        Args:
            threshold: Score drop threshold to consider regression.

        Returns:
            True if overall delta is below threshold.
        """
        return self.overall_delta < threshold

    def regressed_categories(self, threshold: float = -5.0) -> list[str]:
        """List categories that regressed beyond threshold.

        Args:
            threshold: Minimum negative delta.

        Returns:
            List of category names with regressions.
        """
        return [c for c, d in self.category_deltas.items() if d < threshold]

    def improved_categories(self, threshold: float = 5.0) -> list[str]:
        """List categories that improved beyond threshold.

        Args:
            threshold: Minimum positive delta.

        Returns:
            List of category names with improvements.
        """
        return [c for c, d in self.category_deltas.items() if d > threshold]
