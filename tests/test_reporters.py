"""Tests for reporters."""

from pathlib import Path

import pytest

from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)
from agentbench.reporters.console import ConsoleReporter
from agentbench.reporters.html import HTMLReporter
from agentbench.reporters.json import JSONReporter
from agentbench.reporters.markdown import MarkdownReporter


@pytest.fixture
def sample_report() -> ScoreReport:
    tc1 = BenchmarkTestCase(id="t1", name="Test 1", category="injection")
    tc2 = BenchmarkTestCase(id="t2", name="Test 2", category="injection")
    results = [
        BenchmarkResult(test_case=tc1, status=TestStatus.PASSED, score=100.0),
        BenchmarkResult(test_case=tc2, status=TestStatus.FAILED, score=0.0),
    ]
    cats = [
        ScoreCategory(
            name="injection", score=50.0, weight=1.0, tests_passed=1, tests_failed=1, tests_total=2
        ),
    ]
    return ScoreReport(
        agent_id="test-agent",
        agent_version="1.0.0",
        categories=cats,
        overall_score=50.0,
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        duration_seconds=5.5,
        results=results,
    )


class TestJSONReporter:
    def test_generate(self, sample_report: ScoreReport) -> None:
        reporter = JSONReporter()
        output = reporter.generate(sample_report)
        assert '"agent_id": "test-agent"' in output
        assert '"overall_score": 50.0' in output

    def test_save(self, sample_report: ScoreReport, tmp_path: Path) -> None:
        reporter = JSONReporter()
        path = reporter.save(sample_report, tmp_path / "report.json")
        assert Path(path).exists()
        assert Path(path).read_text().startswith("{")

    def test_contains_results(self, sample_report: ScoreReport) -> None:
        reporter = JSONReporter()
        output = reporter.generate(sample_report)
        assert "t1" in output
        assert "t2" in output


class TestHTMLReporter:
    def test_generate(self, sample_report: ScoreReport) -> None:
        reporter = HTMLReporter()
        output = reporter.generate(sample_report)
        assert "<html" in output
        assert "test-agent" in output
        assert "50.0" in output

    def test_save(self, sample_report: ScoreReport, tmp_path: Path) -> None:
        reporter = HTMLReporter()
        path = reporter.save(sample_report, tmp_path / "report.html")
        assert Path(path).exists()
        assert Path(path).read_text().startswith("<!DOCTYPE")

    def test_contains_table(self, sample_report: ScoreReport) -> None:
        reporter = HTMLReporter()
        output = reporter.generate(sample_report)
        assert "t1" in output
        assert "Test 1" in output

    def test_contains_categories(self, sample_report: ScoreReport) -> None:
        reporter = HTMLReporter()
        output = reporter.generate(sample_report)
        assert "injection" in output


class TestMarkdownReporter:
    def test_generate(self, sample_report: ScoreReport) -> None:
        reporter = MarkdownReporter()
        output = reporter.generate(sample_report)
        assert "# AgentBench" in output
        assert "test-agent" in output
        assert "50.0" in output

    def test_save(self, sample_report: ScoreReport, tmp_path: Path) -> None:
        reporter = MarkdownReporter()
        path = reporter.save(sample_report, tmp_path / "report.md")
        assert Path(path).exists()
        assert Path(path).read_text().startswith("# AgentBench")

    def test_contains_table(self, sample_report: ScoreReport) -> None:
        reporter = MarkdownReporter()
        output = reporter.generate(sample_report)
        assert "| t1 |" in output
        assert "| passed |" in output

    def test_empty_report(self) -> None:
        report = ScoreReport(agent_id="empty")
        reporter = MarkdownReporter()
        output = reporter.generate(report)
        assert "empty" in output
        assert "0.0" in output


class TestConsoleReporter:
    def test_print_report(self, sample_report: ScoreReport) -> None:
        reporter = ConsoleReporter()
        # Just verify no exceptions
        reporter.print_report(sample_report)

    def test_print_comparison(self, sample_report: ScoreReport) -> None:
        reporter = ConsoleReporter()
        reporter.print_comparison(sample_report, sample_report)
