"""Tests for --exclude-suites, --tags, merge, MCP suite, severity scoring."""

from pathlib import Path

from typer.testing import CliRunner

from agentbench.cli import app
from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    Severity,
    TestStatus,
)
from agentbench.scorers.metrics import MetricsCalculator
from agentbench.suites.mcp_attack import MCPAttackSuite

runner = CliRunner()


class TestExcludeSuites:
    def test_exclude_one_suite(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection,ssrf",
                "--exclude-suites",
                "ssrf",
                "--dry-run",
            ],
        )
        # excluidas aparecen en warning pero NO en la lista de tests dry-run
        assert result.exit_code == 0
        assert "pi-001" in result.stdout  # prompt_injection tests show
        # ssrf tests should NOT be in the dry-run list
        assert "ssrf-001" not in result.stdout

    def test_exclude_all_no_tests(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--exclude-suites",
                "prompt_injection",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0

    def test_exclude_nonexistent_warns(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--exclude-suites",
                "nonexistent_suite",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "Warning" in result.stdout


class TestTagsFilter:
    def test_tags_filter_includes_matching(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--tags",
                "injection",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "pi-001" in result.stdout

    def test_tags_filter_excludes_non_matching(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--tags",
                "nonexistent_tag_xyz",
                "--dry-run",
            ],
        )
        assert result.exit_code == 0
        assert "No tests to run" not in result.stdout  # just shows nothing


class TestMergeCommand:
    def test_merge_two_reports(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "merged.json"
        result = runner.invoke(
            app,
            [
                "merge",
                str(demo),
                str(demo),
                "--output",
                str(output),
                "--label",
                "merged-agent",
            ],
        )
        assert result.exit_code == 0
        assert output.exists()
        import json

        data = json.loads(output.read_text())
        assert data["agent_id"] == "merged-agent"

    def test_merge_single_report(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "single_merged.json"
        result = runner.invoke(app, ["merge", str(demo), "--output", str(output)])
        assert result.exit_code == 0
        assert output.exists()


class TestMCPAttackSuite:
    def test_suite_generates_cases(self) -> None:
        suite = MCPAttackSuite()
        cases = suite.generate_cases()
        assert len(cases) >= 8
        for tc in cases:
            assert tc.id.startswith("mcp-")

    def test_suite_has_mcp_tags(self) -> None:
        suite = MCPAttackSuite()
        cases = suite.generate_cases()
        for tc in cases:
            assert "mcp" in tc.tags

    def test_suite_registered(self) -> None:
        from agentbench.suites import SUITE_REGISTRY

        assert "mcp_attack" in SUITE_REGISTRY


class TestSeverityScoring:
    def setup_method(self) -> None:
        self.calc = MetricsCalculator(use_severity_weighting=True)

    def _make_result(self, severity: Severity, status: TestStatus) -> BenchmarkResult:
        tc = BenchmarkTestCase(
            id=f"t-{severity.value}",
            name=f"Test {severity.value}",
            category="test",
            severity=severity,
            weight=1.0,
        )
        score = 100.0 if status == TestStatus.PASSED else 0.0
        return BenchmarkResult(test_case=tc, status=status, score=score)

    def test_critical_failure_penalizes_more(self) -> None:
        critical = self._make_result(Severity.CRITICAL, TestStatus.FAILED)
        low = self._make_result(Severity.LOW, TestStatus.FAILED)
        score_critical = self.calc.calculate_category_score([critical])
        score_low = self.calc.calculate_category_score([low])
        assert score_critical < score_low

    def test_medium_failure_partial_penalty(self) -> None:
        medium = self._make_result(Severity.MEDIUM, TestStatus.FAILED)
        score = self.calc.calculate_category_score([medium])
        assert 0 < score < 100

    def test_high_failure_penalty(self) -> None:
        high = self._make_result(Severity.HIGH, TestStatus.FAILED)
        score = self.calc.calculate_category_score([high])
        assert score < 50

    def test_info_treated_like_pass(self) -> None:
        info = self._make_result(Severity.INFO, TestStatus.FAILED)
        score = self.calc.calculate_category_score([info])
        assert score == 100.0

    def test_disabled_severity_weighting(self) -> None:
        calc = MetricsCalculator(use_severity_weighting=False)
        critical = self._make_result(Severity.CRITICAL, TestStatus.FAILED)
        low = self._make_result(Severity.LOW, TestStatus.FAILED)
        assert calc.calculate_category_score([critical]) == calc.calculate_category_score([low])

    def test_mixed_severity_scoring(self) -> None:
        results = [
            self._make_result(Severity.CRITICAL, TestStatus.PASSED),
            self._make_result(Severity.CRITICAL, TestStatus.FAILED),
            self._make_result(Severity.LOW, TestStatus.FAILED),
        ]
        score = self.calc.calculate_category_score(results)
        assert 0 < score < 100
