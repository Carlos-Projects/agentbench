"""Tests for SQLite store, parallel execution, CI mode, and custom indicators."""

from pathlib import Path

import pytest

from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)
from agentbench.runner import BenchmarkRunner
from agentbench.store import BenchmarkStore


@pytest.fixture
def sample_report() -> ScoreReport:
    tc = BenchmarkTestCase(id="t1", name="Test 1", category="injection", prompt="test")
    result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED, score=100.0)
    cat = ScoreCategory(name="injection", score=100.0, tests_total=1, tests_passed=1)
    return ScoreReport(
        agent_id="store-agent",
        agent_version="1.0.0",
        categories=[cat],
        overall_score=100.0,
        total_tests=1,
        passed_tests=1,
        results=[result],
    )


class TestBenchmarkStore:
    def test_init_creates_tables(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        BenchmarkStore(db_path=db)
        assert db.exists()

    def test_save_and_list(self, tmp_path: Path, sample_report: ScoreReport) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        run_id = store.save(sample_report)
        assert run_id is not None

        runs = store.list_runs()
        assert len(runs) == 1
        assert runs[0]["agent_id"] == "store-agent"

    def test_list_filter_by_agent(self, tmp_path: Path, sample_report: ScoreReport) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        store.save(sample_report)
        runs = store.list_runs(agent_id="store-agent")
        assert len(runs) == 1
        runs = store.list_runs(agent_id="nonexistent")
        assert len(runs) == 0

    def test_get_run(self, tmp_path: Path, sample_report: ScoreReport) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        run_id = store.save(sample_report)
        run = store.get_run(run_id)
        assert run is not None
        assert run["agent_id"] == "store-agent"
        assert run["overall_score"] == 100.0

    def test_get_run_not_found(self, tmp_path: Path) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        assert store.get_run(999) is None

    def test_get_run_with_results(self, tmp_path: Path, sample_report: ScoreReport) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        run_id = store.save(sample_report)
        run = store.get_run(run_id)
        assert len(run["results"]) == 1
        assert run["results"][0]["test_id"] == "t1"

    def test_delete_old_runs(self, tmp_path: Path) -> None:
        store = BenchmarkStore(db_path=tmp_path / "test.db")
        for _ in range(5):
            r = ScoreReport(agent_id="agent", overall_score=50.0, total_tests=0)
            store.save(r)
        deleted = store.delete_old_runs(keep=2)
        assert deleted == 3
        runs = store.list_runs()
        assert len(runs) == 2


class TestParallelExecution:
    @pytest.mark.asyncio
    async def test_runner_parallel_initialization(self) -> None:
        runner = BenchmarkRunner(target_url="http://test:8080", parallel=3)
        assert runner.parallel == 3

    @pytest.mark.asyncio
    async def test_runner_parallel_does_not_break_error(self) -> None:
        runner = BenchmarkRunner(target_url="http://test:8080", parallel=3)
        tc = BenchmarkTestCase(id="p1", name="Parallel", category="test", prompt="hello")
        result = await runner._execute_test(tc, "http://test:8080")
        assert result.status in (TestStatus.ERROR, TestStatus.TIMEOUT)


class TestCustomIndicators:
    def test_detect_failure_custom_indicators(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="c1", name="Custom", category="test")
        assert runner._detect_failure("custom block word", tc, custom_indicators=["custom block"]) is True

    def test_detect_failure_custom_not_found(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="c2", name="Custom", category="test")
        assert runner._detect_failure("safe response", tc, custom_indicators=["custom block"]) is False

    def test_detect_failure_default_indicators(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="c3", name="Default", category="test")
        assert runner._detect_failure("i have been hacked", tc) is True

    def test_custom_indicators_empty_list(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="c4", name="Empty", category="test")
        assert runner._detect_failure("anything", tc, custom_indicators=[]) is False

    def test_prompt_injection_suite_has_custom_indicators(self) -> None:
        from agentbench.suites.prompt_injection import PromptInjectionSuite

        suite = PromptInjectionSuite()
        assert len(suite.failure_indicators) > 0


class TestCIMode:
    def test_report_scoring(self) -> None:
        cat = ScoreCategory(name="test", score=50.0, tests_total=1, tests_failed=1)
        report = ScoreReport(agent_id="ci-agent", categories=[cat], overall_score=50.0, total_tests=1, failed_tests=1)
        assert report.overall_score == 50.0
        assert report.overall_score < 80.0

    def test_report_passing(self) -> None:
        cat = ScoreCategory(name="test", score=95.0, tests_total=1, tests_passed=1)
        report = ScoreReport(agent_id="ci-agent", categories=[cat], overall_score=95.0, total_tests=1, passed_tests=1)
        assert report.overall_score >= 80.0
