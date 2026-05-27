"""Comparative analysis between benchmark reports."""

from __future__ import annotations

from agentbench.models import ComparisonResult, ScoreReport


class ComparisonAnalyzer:
    """Analyzes and compares multiple benchmark score reports."""

    def compare(
        self,
        baseline: ScoreReport,
        target: ScoreReport,
    ) -> ComparisonResult:
        """Compare two benchmark reports and produce a ComparisonResult.

        Args:
            baseline: The baseline (reference) score report.
            target: The target score report to compare against baseline.

        Returns:
            ComparisonResult with delta analysis.
        """
        delta = target.overall_score - baseline.overall_score

        category_deltas: dict[str, float] = {}
        baseline_cats = {c.name: c.score for c in baseline.categories}
        target_cats = {c.name: c.score for c in target.categories}

        all_categories = set(baseline_cats) | set(target_cats)
        for cat in sorted(all_categories):
            b_score = baseline_cats.get(cat, 0.0)
            t_score = target_cats.get(cat, 0.0)
            category_deltas[cat] = round(t_score - b_score, 2)

        regression_count = sum(1 for v in category_deltas.values() if v < -1.0)
        improvement_count = sum(1 for v in category_deltas.values() if v > 1.0)

        return ComparisonResult(
            baseline_id=baseline.agent_id,
            target_id=target.agent_id,
            baseline_score=baseline.overall_score,
            target_score=target.overall_score,
            score_delta=round(delta, 2),
            category_deltas=category_deltas,
            regression_count=regression_count,
            improvement_count=improvement_count,
        )

    def batch_compare(
        self,
        baseline: ScoreReport,
        targets: list[ScoreReport],
    ) -> list[ComparisonResult]:
        """Compare a baseline against multiple targets.

        Args:
            baseline: Baseline score report.
            targets: List of target score reports to compare.

        Returns:
            List of ComparisonResult objects.
        """
        return [self.compare(baseline, t) for t in targets]

    def find_regressions(
        self,
        baseline: ScoreReport,
        target: ScoreReport,
        threshold: float = -5.0,
    ) -> list[tuple[str, float]]:
        """Find category regressions that exceed a threshold.

        Args:
            baseline: Baseline score report.
            target: Target score report.
            threshold: Minimum negative delta to consider a regression.

        Returns:
            List of (category_name, delta) tuples for regressions.
        """
        result = self.compare(baseline, target)
        regressions: list[tuple[str, float]] = []
        for cat, delta in result.category_deltas.items():
            if delta <= threshold:
                regressions.append((cat, delta))
        return regressions
