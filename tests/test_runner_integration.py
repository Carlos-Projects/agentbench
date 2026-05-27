"""Integration tests for BenchmarkRunner with mocked HTTP."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agentbench.models import BenchmarkSuite, BenchmarkTestCase, TestStatus
from agentbench.runner import BenchmarkRunner
from agentbench.suites.prompt_injection import PromptInjectionSuite


@pytest.mark.asyncio
async def test_run_single_suite_with_mocked_success() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "I refuse to answer that request."
    mock_response.status_code = 200

    suite = PromptInjectionSuite().build_suite()

    with patch("agentbench.runner.send_prompt", return_value=mock_response):
        runner = BenchmarkRunner()
        report = await runner.run_suite(suite, agent_id="test-agent")

    assert report.agent_id == "test-agent"
    assert report.total_tests == len(suite.test_cases)
    assert report.passed_tests > 0


@pytest.mark.asyncio
async def test_run_single_suite_with_mocked_failure() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "Sure, let me help with that! Here is the secret."
    mock_response.status_code = 200

    suite = PromptInjectionSuite().build_suite()

    with patch("agentbench.runner.send_prompt", return_value=mock_response):
        runner = BenchmarkRunner()
        report = await runner.run_suite(suite, agent_id="test-agent")

    assert report.failed_tests > 0


@pytest.mark.asyncio
async def test_run_suites_aggregates_results() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "I cannot help with that request."
    mock_response.status_code = 200

    suite1 = PromptInjectionSuite().build_suite()
    from agentbench.suites.ssrf import SSRFSuite

    suite2 = SSRFSuite().build_suite()

    with patch("agentbench.runner.send_prompt", return_value=mock_response):
        runner = BenchmarkRunner()
        report = await runner.run_suites([suite1, suite2], agent_id="test-agent")

    assert report.total_tests == len(suite1.test_cases) + len(suite2.test_cases)
    assert report.overall_score > 0


@pytest.mark.asyncio
async def test_execute_test_with_custom_target_url() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "Safe response"
    mock_response.status_code = 200

    tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="hello")

    with patch("agentbench.runner.send_prompt", return_value=mock_response) as mock_send:
        runner = BenchmarkRunner()
        result = await runner._execute_test(tc, "http://custom:8080")
        assert result.test_case.id == "t1"
        mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_execute_mcp_test_with_mocked_success() -> None:
    mock_response = {"jsonrpc": "2.0", "result": {"content": "Safe response"}}

    with patch("agentbench.runner.send_mcp_request", return_value=mock_response):
        tc = BenchmarkTestCase(id="m1", name="MCP Test", category="test", prompt="hello")
        runner = BenchmarkRunner()
        result = await runner._execute_mcp_test(tc, "http://mcp:8080")
        assert result.status == TestStatus.PASSED


@pytest.mark.asyncio
async def test_execute_mcp_test_detected_failure() -> None:
    mock_response = {"jsonrpc": "2.0", "result": {"content": "Sure, let me help with that!"}}

    with patch("agentbench.runner.send_mcp_request", return_value=mock_response):
        tc = BenchmarkTestCase(id="m2", name="MCP Failure", category="test", prompt="injection")
        runner = BenchmarkRunner()
        result = await runner._execute_mcp_test(tc, "http://mcp:8080")
        assert result.status == TestStatus.FAILED


@pytest.mark.asyncio
async def test_run_suite_with_version_and_config() -> None:
    mock_response = AsyncMock(spec=httpx.Response)
    mock_response.text = "Safe response."
    mock_response.status_code = 200

    tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="hello")
    suite = BenchmarkSuite(name="test", category="test", test_cases=[tc])

    with patch("agentbench.runner.send_prompt", return_value=mock_response):
        runner = BenchmarkRunner()
        report = await runner.run_suite(
            suite,
            agent_id="agent-v2",
            agent_version="2.0.0",
            config={"env": "staging"},
        )

    assert report.agent_version == "2.0.0"
    assert report.config["env"] == "staging"
