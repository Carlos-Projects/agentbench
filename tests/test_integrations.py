"""Tests for MCPGuard and MCPscop integrations."""

import json
from pathlib import Path

import pytest

from agentbench.integrations.mcpguard import MCPGuardPolicyGenerator
from agentbench.integrations.mcpscop import MCPscopExporter
from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)


@pytest.fixture
def failed_report() -> ScoreReport:
    tc1 = BenchmarkTestCase(id="pi-001", name="Direct injection", category="prompt_injection", prompt="test", weight=2.0)
    tc2 = BenchmarkTestCase(id="tp-001", name="Tool injection", category="tool_poisoning", prompt="test", weight=2.0)
    tc3 = BenchmarkTestCase(id="ssrf-001", name="SSRF test", category="ssrf", prompt="test", weight=2.0)
    results = [
        BenchmarkResult(test_case=tc1, status=TestStatus.FAILED, score=0.0, detected=True),
        BenchmarkResult(test_case=tc2, status=TestStatus.FAILED, score=0.0, detected=True),
        BenchmarkResult(test_case=tc3, status=TestStatus.FAILED, score=0.0, detected=True),
    ]
    cats = [
        ScoreCategory(name="prompt_injection", score=0.0, tests_total=1, tests_failed=1),
        ScoreCategory(name="tool_poisoning", score=0.0, tests_total=1, tests_failed=1),
        ScoreCategory(name="ssrf", score=0.0, tests_total=1, tests_failed=1),
    ]
    return ScoreReport(
        agent_id="test-agent",
        categories=cats,
        overall_score=0.0,
        total_tests=3,
        passed_tests=0,
        failed_tests=3,
        results=results,
        config={"target": "http://test-server:8080"},
    )


class TestMCPGuardPolicyGenerator:
    def test_generate_sets_block_flags(self, failed_report: ScoreReport) -> None:
        gen = MCPGuardPolicyGenerator()
        policy = gen.generate(failed_report)
        assert policy["block_on_injection"] is True
        assert policy["block_on_poisoning"] is True
        assert policy["block_on_resource_scan"] is True

    def test_generate_deny_list(self, failed_report: ScoreReport) -> None:
        gen = MCPGuardPolicyGenerator()
        policy = gen.generate(failed_report)
        assert len(policy["deny"]) > 0

    def test_generate_rate_limit_low_score(self, failed_report: ScoreReport) -> None:
        gen = MCPGuardPolicyGenerator()
        policy = gen.generate(failed_report)
        assert policy["rate_limit"] >= 20

    def test_generate_high_score_no_rate_restriction(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="test")
        result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED, score=100.0)
        cat = ScoreCategory(name="test", score=95.0, tests_total=1, tests_passed=1)
        report = ScoreReport(
            agent_id="good-agent",
            categories=[cat],
            overall_score=95.0,
            total_tests=1,
            passed_tests=1,
            results=[result],
        )
        gen = MCPGuardPolicyGenerator()
        policy = gen.generate(report)
        assert policy["block_on_injection"] is False
        assert policy["rate_limit"] == 100

    def test_save_yaml(self, failed_report: ScoreReport, tmp_path: Path) -> None:
        gen = MCPGuardPolicyGenerator()
        path = gen.save_yaml(failed_report, tmp_path / "mcpguard.yaml")
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "block_on_injection: true" in content

    def test_no_failed_tests_does_not_block(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="prompt_injection", prompt="test")
        result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED, score=100.0)
        cat = ScoreCategory(name="prompt_injection", score=100.0, tests_total=1, tests_passed=1)
        report = ScoreReport(
            agent_id="agent",
            categories=[cat],
            overall_score=100.0,
            total_tests=1,
            passed_tests=1,
            results=[result],
        )
        gen = MCPGuardPolicyGenerator()
        policy = gen.generate(report)
        assert policy["block_on_injection"] is False


class TestMCPscopExporter:
    def test_to_security_events(self, failed_report: ScoreReport) -> None:
        exporter = MCPscopExporter()
        events = exporter.to_security_events(failed_report)
        assert len(events) == 3
        assert events[0]["source"] == "agentbench"
        assert events[0]["event_type"] == "prompt_injection"

    def test_to_security_events_no_failures(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="test")
        result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED, score=100.0)
        cat = ScoreCategory(name="test", score=100.0, tests_total=1, tests_passed=1)
        report = ScoreReport(
            agent_id="agent",
            categories=[cat],
            overall_score=100.0,
            total_tests=1,
            passed_tests=1,
            results=[result],
        )
        exporter = MCPscopExporter()
        events = exporter.to_security_events(report)
        assert len(events) == 0

    def test_to_findings(self, failed_report: ScoreReport) -> None:
        exporter = MCPscopExporter()
        findings = exporter.to_findings(failed_report)
        assert len(findings) == 3
        assert findings[0]["scanner"] == "agentbench"

    def test_save_events_json(self, failed_report: ScoreReport, tmp_path: Path) -> None:
        exporter = MCPscopExporter()
        path = exporter.save_events_json(failed_report, tmp_path / "events.json")
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert len(data) == 3

    def test_save_findings_json(self, failed_report: ScoreReport, tmp_path: Path) -> None:
        exporter = MCPscopExporter()
        path = exporter.save_findings_json(failed_report, tmp_path / "findings.json")
        assert Path(path).exists()
        data = json.loads(Path(path).read_text())
        assert len(data) == 3

    def test_recommendation(self) -> None:
        exporter = MCPscopExporter()
        assert "No action" in exporter._recommendation(95.0)
        assert "Review" in exporter._recommendation(75.0)
        assert "Implement" in exporter._recommendation(60.0)
        assert "Urgent" in exporter._recommendation(30.0)
