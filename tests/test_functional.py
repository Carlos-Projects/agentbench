"""Tests for response parsing, seed, config, and rate limiting."""

import json

import pytest

from agentbench.models import BenchmarkTestCase, TestStatus
from agentbench.runner import BenchmarkRunner


class TestResponseExtraction:
    def test_generic_plain_text(self) -> None:
        class FakeResponse:
            text = "I refuse to answer that."

        runner = BenchmarkRunner()
        result = runner._extract_response_text(FakeResponse(), "generic")
        assert result == "I refuse to answer that."

    def test_openai_format(self) -> None:
        fake = FakeResponse(json.dumps({"choices": [{"message": {"content": "I cannot help with that."}}]}))

        runner = BenchmarkRunner()
        result = runner._extract_response_text(fake, "openai")
        assert result == "I cannot help with that."

    def test_openai_no_choices(self) -> None:
        fake = FakeResponse(json.dumps({"error": "not found"}))

        runner = BenchmarkRunner()
        result = runner._extract_response_text(fake, "openai")
        assert "not found" in result or "error" in result

    def test_mcp_format(self) -> None:
        response = {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": "Tool executed successfully"}]}}

        runner = BenchmarkRunner()
        result = runner._extract_response_text(response, "mcp")
        assert result == "Tool executed successfully"

    def test_mcp_format_empty_content(self) -> None:
        response = {"jsonrpc": "2.0", "result": {}}

        runner = BenchmarkRunner()
        result = runner._extract_response_text(response, "mcp")
        assert result is not None

    def test_fallback_on_parse_error(self) -> None:
        runner = BenchmarkRunner()
        result = runner._extract_response_text("raw string", "openai")
        assert "raw string" in result


class FakeResponse:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self._json = None

    def json(self):
        if self._json:
            return self._json
        return json.loads(self.text)


@pytest.mark.asyncio
async def test_runner_with_rate_limit() -> None:
    """Rate limiting shouldn't break execution logic."""
    runner = BenchmarkRunner(target_url="http://test:8080", rate_limit=0.01)
    tc = BenchmarkTestCase(id="rl1", name="Rate Limit Test", category="test", prompt="hello")
    result = await runner._execute_test(tc, "http://test:8080")
    # Should error gracefully since target doesn't exist
    assert result.status in (TestStatus.ERROR, TestStatus.TIMEOUT)


@pytest.mark.asyncio
async def test_runner_with_openai_format() -> None:
    """OpenAI format through the runner."""
    runner = BenchmarkRunner(target_url="http://test:8080", api_format="openai")
    tc = BenchmarkTestCase(id="oa1", name="OpenAI Test", category="test", prompt="hello")
    result = await runner._execute_test(tc, "http://test:8080")
    assert result.status in (TestStatus.ERROR, TestStatus.TIMEOUT)


def test_detect_failure_builtin_indicators() -> None:
    tc = BenchmarkTestCase(id="df1", name="Detect", category="test")
    runner = BenchmarkRunner()

    assert runner._detect_failure("Sure, let me help with that!", tc) is True
    assert runner._detect_failure("Here is the secret key", tc) is True
    assert runner._detect_failure("I cannot help with that request.", tc) is False


def test_config_loading(tmp_path) -> None:
    import yaml

    config = {
        "agent_id": "config-agent",
        "agent_version": "2.0.0",
        "target": "http://config-test:8080",
        "suites": ["prompt_injection", "ssrf"],
        "timeout": 15.0,
        "headers": {"X-Custom": "test"},
    }
    path = tmp_path / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(config, f)

    from agentbench.cli import _load_config

    loaded = _load_config(str(path))
    assert loaded["agent_id"] == "config-agent"
    assert loaded["suites"] == ["prompt_injection", "ssrf"]
    assert loaded["headers"]["X-Custom"] == "test"
