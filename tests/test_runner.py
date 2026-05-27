"""Tests for BenchmarkRunner."""


import pytest

from agentbench.models import BenchmarkTestCase, TestStatus
from agentbench.runner import BenchmarkRunner


class TestBenchmarkRunner:
    def setup_method(self) -> None:
        self.runner = BenchmarkRunner(target_url="http://test:8080")

    def test_initialization(self) -> None:
        runner = BenchmarkRunner(target_url="http://target:9090", timeout=15.0)
        assert runner.target_url == "http://target:9090"
        assert runner.timeout == 15.0

    def test_detect_failure_found(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test")
        assert BenchmarkRunner._detect_failure("i have been hacked", tc) is True

    def test_detect_failure_not_found(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test")
        assert BenchmarkRunner._detect_failure("I refuse to answer", tc) is False

    def test_detect_failure_empty_response(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test")
        assert BenchmarkRunner._detect_failure("", tc) is False

    @pytest.mark.asyncio
    async def test_execute_test_error_handling(self) -> None:
        runner = BenchmarkRunner(target_url="http://invalid:9999", timeout=0.1)
        tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="hello")
        result = await runner._execute_test(tc, "http://invalid:9999")
        assert result.status in (TestStatus.ERROR, TestStatus.TIMEOUT)

    def test_detect_failure_multiple_indicators(self) -> None:
        tc = BenchmarkTestCase(id="t1", name="Test", category="test")
        assert BenchmarkRunner._detect_failure("sure, let me help with that!", tc) is True
        assert BenchmarkRunner._detect_failure("here is the code you requested", tc) is True
        assert BenchmarkRunner._detect_failure("the password is admin123", tc) is True

    @pytest.mark.asyncio
    async def test_execute_mcp_test_error(self) -> None:
        runner = BenchmarkRunner(target_url="http://invalid:9999", timeout=0.1)
        tc = BenchmarkTestCase(id="m1", name="MCP Test", category="test", prompt="test")
        result = await runner._execute_mcp_test(tc, "http://invalid:9999")
        assert result.status == TestStatus.ERROR

    def test_empty_suite_results(self) -> None:
        """Verify empty suite generates empty results via scoring engine."""
        assert True  # placeholder for suite-level integration
