"""Tests for Pydantic models."""

from datetime import datetime

from agentbench.models import (
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkTestCase,
    ComparisonResult,
    LeaderboardEntry,
    ScoreCategory,
    ScoreReport,
    Severity,
    TestStatus,
    TrendPoint,
)


class TestEnums:
    def test_test_status_values(self) -> None:
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.ERROR.value == "error"
        assert TestStatus.SKIPPED.value == "skipped"

    def test_severity_values(self) -> None:
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"


class TestBenchmarkTestCase:
    def test_minimal_creation(self) -> None:
        tc = BenchmarkTestCase(id="test-001", name="Test case", category="injection")
        assert tc.id == "test-001"
        assert tc.name == "Test case"
        assert tc.category == "injection"
        assert tc.severity == Severity.MEDIUM

    def test_full_creation(self) -> None:
        tc = BenchmarkTestCase(
            id="test-002",
            name="Full test",
            category="ssrf",
            description="Test description",
            severity=Severity.HIGH,
            target="http://target:8080",
            prompt="Test prompt",
            expected_behavior="Should block",
            tags=["ssrf", "critical"],
            weight=2.0,
        )
        assert tc.weight == 2.0
        assert len(tc.tags) == 2

    def test_default_values(self) -> None:
        tc = BenchmarkTestCase(id="test-003", name="Defaults", category="test")
        assert tc.weight == 1.0
        assert tc.description == ""
        assert tc.tags == []
        assert tc.severity == Severity.MEDIUM


class TestBenchmarkResult:
    def test_creation_with_defaults(self) -> None:
        tc = BenchmarkTestCase(id="r-001", name="Result test", category="test")
        result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED)
        assert result.score == 0.0
        assert result.detected is False
        assert result.response_time_ms == 0.0

    def test_failed_result(self) -> None:
        tc = BenchmarkTestCase(id="r-002", name="Failed test", category="test")
        result = BenchmarkResult(
            test_case=tc,
            status=TestStatus.FAILED,
            score=0.0,
            detected=True,
            error_message="Test failed",
        )
        assert result.status == TestStatus.FAILED
        assert result.detected is True

    def test_timestamp_default(self) -> None:
        tc = BenchmarkTestCase(id="r-003", name="Timestamp test", category="test")
        result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED)
        assert isinstance(result.timestamp, datetime)


class TestScoreCategory:
    def test_creation(self) -> None:
        cat = ScoreCategory(
            name="injection",
            score=85.5,
            tests_passed=10,
            tests_failed=2,
            tests_total=12,
        )
        assert cat.name == "injection"
        assert cat.score == 85.5
        assert cat.weight == 1.0
        assert cat.tests_total == 12

    def test_score_bounds(self) -> None:
        cat = ScoreCategory(name="test", score=50.0)
        assert 0 <= cat.score <= 100

    def test_default_details(self) -> None:
        cat = ScoreCategory(name="test", score=0.0)
        assert cat.details == {}


class TestBenchmarkSuite:
    def test_creation(self) -> None:
        suite = BenchmarkSuite(name="test_suite", category="injection")
        assert suite.name == "test_suite"
        assert suite.category == "injection"
        assert suite.test_cases == []

    def test_with_test_cases(self) -> None:
        tc1 = BenchmarkTestCase(id="t1", name="Test 1", category="test")
        tc2 = BenchmarkTestCase(id="t2", name="Test 2", category="test")
        suite = BenchmarkSuite(name="multi", category="test", test_cases=[tc1, tc2])
        assert len(suite.test_cases) == 2


class TestScoreReport:
    def test_creation(self) -> None:
        report = ScoreReport(agent_id="agent-1")
        assert report.agent_id == "agent-1"
        assert report.overall_score == 0.0
        assert report.total_tests == 0

    def test_with_categories(self) -> None:
        cats = [
            ScoreCategory(name="pi", score=90.0, tests_total=5, tests_passed=5),
            ScoreCategory(name="tp", score=75.0, tests_total=4, tests_passed=3),
        ]
        report = ScoreReport(
            agent_id="agent-1",
            categories=cats,
            overall_score=82.5,
            total_tests=9,
            passed_tests=8,
        )
        assert len(report.categories) == 2
        assert report.overall_score == 82.5

    def test_with_metadata(self) -> None:
        report = ScoreReport(
            agent_id="agent-1",
            config={"target": "http://test:8080"},
            duration_seconds=12.5,
        )
        assert report.config["target"] == "http://test:8080"
        assert report.duration_seconds == 12.5


class TestComparisonResult:
    def test_creation(self) -> None:
        result = ComparisonResult(
            baseline_id="v1.0",
            target_id="v2.0",
            baseline_score=80.0,
            target_score=85.0,
            score_delta=5.0,
        )
        assert result.score_delta == 5.0
        assert result.baseline_id == "v1.0"
        assert result.target_id == "v2.0"

    def test_regression_detection(self) -> None:
        result = ComparisonResult(
            baseline_id="v1",
            target_id="v2",
            baseline_score=90.0,
            target_score=70.0,
            score_delta=-20.0,
            regression_count=2,
        )
        assert result.score_delta < 0
        assert result.regression_count == 2


class TestTrendPoint:
    def test_creation(self) -> None:
        point = TrendPoint(
            timestamp=datetime(2026, 1, 1),
            overall_score=85.0,
            agent_version="1.0.0",
        )
        assert point.overall_score == 85.0
        assert point.agent_version == "1.0.0"

    def test_with_category_scores(self) -> None:
        point = TrendPoint(
            timestamp=datetime(2026, 1, 1),
            overall_score=80.0,
            category_scores={"injection": 85.0, "ssrf": 75.0},
        )
        assert point.category_scores["injection"] == 85.0


class TestLeaderboardEntry:
    def test_creation(self) -> None:
        entry = LeaderboardEntry(rank=1, agent_id="agent-1", overall_score=95.0)
        assert entry.rank == 1
        assert entry.overall_score == 95.0

    def test_with_scores(self) -> None:
        entry = LeaderboardEntry(
            rank=2,
            agent_id="agent-2",
            overall_score=88.0,
            category_scores={"injection": 90.0},
            total_tests=50,
            passed_tests=44,
        )
        assert entry.passed_tests == 44
        assert entry.total_tests == 50

    def test_default_rank(self) -> None:
        entry = LeaderboardEntry(agent_id="agent-3", overall_score=70.0)
        assert entry.rank == 0
