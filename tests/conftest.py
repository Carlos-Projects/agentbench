"""Shared test fixtures for AgentBench tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentbench.models import (
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)


@pytest.fixture
def sample_report() -> ScoreReport:
    """A sample ScoreReport for use in reporter and comparison tests."""
    tc1 = BenchmarkTestCase(id="t1", name="Test 1", category="injection")
    tc2 = BenchmarkTestCase(id="t2", name="Test 2", category="injection")
    results = [
        BenchmarkResult(test_case=tc1, status=TestStatus.PASSED, score=100.0),
        BenchmarkResult(test_case=tc2, status=TestStatus.FAILED, score=0.0),
    ]
    cats = [
        ScoreCategory(
            name="injection",
            score=50.0,
            weight=1.0,
            tests_passed=1,
            tests_failed=1,
            tests_total=2,
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


@pytest.fixture
def sample_suite() -> BenchmarkSuite:
    """A minimal benchmark suite for runner tests."""
    return BenchmarkSuite(
        name="test_suite",
        category="test",
        description="A test suite",
        test_cases=[
            BenchmarkTestCase(id="st1", name="Suite Test 1", category="test", prompt="safe prompt"),
            BenchmarkTestCase(id="st2", name="Suite Test 2", category="test", prompt="another prompt"),
        ],
    )


@pytest.fixture
def demo_results_path() -> Path:
    """Path to the demo_results.json example file."""
    return Path(__file__).parent.parent / "examples" / "demo_results.json"


@pytest.fixture
def multiple_reports() -> list[ScoreReport]:
    """Multiple score reports for leaderboard and trend tests."""
    reports: list[ScoreReport] = []
    for i, (agent, score) in enumerate([("alpha", 90.0), ("beta", 75.0), ("gamma", 60.0)]):
        cats = [ScoreCategory(name="test", score=score, tests_total=1, tests_passed=int(score > 50))]
        reports.append(
            ScoreReport(
                agent_id=agent,
                agent_version=f"1.{i}.0",
                categories=cats,
                overall_score=score,
                total_tests=1,
                passed_tests=int(score > 50),
            )
        )
    return reports
