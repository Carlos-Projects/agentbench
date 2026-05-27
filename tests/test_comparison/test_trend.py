"""Tests for TrendAnalyzer."""

from datetime import datetime, timedelta

from agentbench.comparison.trend import TrendAnalyzer
from agentbench.models import ScoreCategory, ScoreReport


class TestTrendAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = TrendAnalyzer()

    def _make_report(self, score: float, day: int = 0, version: str = "1.0") -> ScoreReport:
        timestamp = datetime(2026, 1, 1) + timedelta(days=day)
        cats = [
            ScoreCategory(name="test", score=score, tests_total=1, tests_passed=int(score > 50))
        ]
        return ScoreReport(
            agent_id="agent-1",
            agent_version=version,
            categories=cats,
            overall_score=score,
            total_tests=1,
            timestamp=timestamp,
        )

    def test_build_trend(self) -> None:
        reports = [self._make_report(80.0, 0), self._make_report(85.0, 1)]
        trend = self.analyzer.build_trend(reports)
        assert len(trend) == 2
        assert trend[0].overall_score == 80.0
        assert trend[1].overall_score == 85.0

    def test_build_trend_with_category_scores(self) -> None:
        reports = [self._make_report(80.0)]
        trend = self.analyzer.build_trend(reports)
        assert "test" in trend[0].category_scores

    def test_compute_moving_average(self) -> None:
        reports = [self._make_report(80.0, i) for i in range(5)]
        trend = self.analyzer.build_trend(reports)
        avg = self.analyzer.compute_moving_average(trend, window=3)
        assert len(avg) == 5

    def test_moving_average_short_window(self) -> None:
        reports = [self._make_report(80.0)]
        trend = self.analyzer.build_trend(reports)
        avg = self.analyzer.compute_moving_average(trend, window=3)
        assert len(avg) == 1

    def test_detect_improving(self) -> None:
        reports = [self._make_report(60.0, i) for i in range(5)]
        trend = self.analyzer.build_trend(reports)
        # Increase scores
        for i, p in enumerate(trend):
            p.overall_score = 60.0 + i * 8.0
        direction = self.analyzer.detect_trend_direction(trend)
        assert direction == "improving"

    def test_detect_declining(self) -> None:
        reports = [self._make_report(80.0, i) for i in range(5)]
        trend = self.analyzer.build_trend(reports)
        for i, p in enumerate(trend):
            p.overall_score = 80.0 - i * 8.0
        direction = self.analyzer.detect_trend_direction(trend)
        assert direction == "declining"

    def test_detect_stable(self) -> None:
        reports = [self._make_report(75.0, i) for i in range(3)]
        trend = self.analyzer.build_trend(reports)
        direction = self.analyzer.detect_trend_direction(trend)
        assert direction == "stable"

    def test_detect_single_point(self) -> None:
        reports = [self._make_report(80.0)]
        trend = self.analyzer.build_trend(reports)
        assert self.analyzer.detect_trend_direction(trend) == "stable"

    def test_volatility(self) -> None:
        reports = [self._make_report(80.0, i) for i in range(3)]
        trend = self.analyzer.build_trend(reports)
        vol = self.analyzer.volatility(trend)
        assert vol >= 0.0

    def test_volatility_single_point(self) -> None:
        reports = [self._make_report(80.0)]
        trend = self.analyzer.build_trend(reports)
        assert self.analyzer.volatility(trend) == 0.0

    def test_estimate_next_score(self) -> None:
        reports = [self._make_report(70.0, i) for i in range(3)]
        trend = self.analyzer.build_trend(reports)
        for i, p in enumerate(trend):
            p.overall_score = 70.0 + i * 5.0
        predicted = self.analyzer.estimate_next_score(trend)
        assert 70.0 <= predicted <= 100.0

    def test_estimate_next_score_single(self) -> None:
        reports = [self._make_report(80.0)]
        trend = self.analyzer.build_trend(reports)
        assert self.analyzer.estimate_next_score(trend) == 80.0
