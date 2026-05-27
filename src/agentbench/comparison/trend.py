"""Trend analysis for benchmark scores over time."""

from __future__ import annotations

import statistics

import numpy as np

from agentbench.models import ScoreReport, TrendPoint


class TrendAnalyzer:
    """Analyzes trends in benchmark scores over time."""

    def build_trend(self, reports: list[ScoreReport]) -> list[TrendPoint]:
        """Build a trend from a chronological list of score reports.

        Args:
            reports: Chronologically ordered score reports.

        Returns:
            List of TrendPoint objects.
        """
        trend: list[TrendPoint] = []
        for report in reports:
            category_scores = {c.name: c.score for c in report.categories}
            trend.append(
                TrendPoint(
                    timestamp=report.timestamp,
                    overall_score=report.overall_score,
                    category_scores=category_scores,
                    total_tests=report.total_tests,
                    agent_version=report.agent_version,
                )
            )
        return trend

    def compute_moving_average(
        self,
        trend: list[TrendPoint],
        window: int = 3,
    ) -> list[float]:
        """Compute moving average of overall scores.

        Args:
            trend: List of trend points.
            window: Moving average window size.

        Returns:
            List of moving average values.
        """
        scores = [p.overall_score for p in trend]
        if len(scores) < window:
            return scores.copy()

        averages: list[float] = []
        for i in range(len(scores)):
            start = max(0, i - window + 1)
            chunk = scores[start : i + 1]
            averages.append(sum(chunk) / len(chunk))
        return averages

    def detect_trend_direction(self, trend: list[TrendPoint]) -> str:
        """Detect the overall direction of the trend.

        Args:
            trend: List of trend points.

        Returns:
            'improving', 'declining', or 'stable'.
        """
        if len(trend) < 2:
            return "stable"

        scores = [p.overall_score for p in trend]
        x = np.arange(len(scores))
        if np.std(x) == 0:
            return "stable"
        slope = np.polyfit(x, scores, 1)[0]

        if slope > 0.5:
            return "improving"
        if slope < -0.5:
            return "declining"
        return "stable"

    def volatility(self, trend: list[TrendPoint]) -> float:
        """Calculate score volatility (standard deviation).

        Args:
            trend: List of trend points.

        Returns:
            Standard deviation of overall scores.
        """
        if len(trend) < 2:
            return 0.0
        scores = [p.overall_score for p in trend]
        return float(statistics.stdev(scores))

    def estimate_next_score(self, trend: list[TrendPoint]) -> float:
        """Estimate the next score using linear regression.

        Args:
            trend: List of trend points.

        Returns:
            Predicted next overall score.
        """
        if len(trend) < 2:
            return trend[-1].overall_score if trend else 0.0

        scores = [p.overall_score for p in trend]
        x = np.arange(len(scores))
        slope, intercept = np.polyfit(x, scores, 1)
        next_x = len(scores)
        predicted = slope * next_x + intercept
        return max(0.0, min(100.0, predicted))
