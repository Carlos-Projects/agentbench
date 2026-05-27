"""Tests for CLI run command features: anthropic, --store, --webhook, --retry, --plugin-dir, --log-format, --verbose/--quiet."""

import json
from pathlib import Path

from typer.testing import CliRunner

from agentbench.cli import app
from agentbench.models import BenchmarkTestCase
from agentbench.runner import BenchmarkRunner

runner = CliRunner()


class TestRunWithStore:
    def test_run_with_store_flag(self, tmp_path: Path) -> None:
        """Test that --store saves results to SQLite during a run."""
        db = tmp_path / "test_run.db"
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--store",
                "--db",
                str(db),
            ],
        )
        assert result.exit_code == 0
        assert "Saved to store" in result.stdout
        assert db.exists()


class TestRunWithVerboseQuiet:
    def test_run_verbose(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--verbose",
            ],
        )
        assert result.exit_code == 0

    def test_run_quiet(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--quiet",
            ],
        )
        assert result.exit_code == 0


class TestRunWithRetry:
    def test_run_retry(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--retry",
                "2",
            ],
        )
        assert result.exit_code == 0


class TestRunWithFormat:
    def test_run_anthropic(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--api-format",
                "anthropic",
            ],
        )
        assert result.exit_code == 0

    def test_run_mcp(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--api-format",
                "mcp",
            ],
        )
        assert result.exit_code == 0

    def test_run_log_format_json(self) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--log-format",
                "json",
            ],
        )
        assert result.exit_code == 0


class TestRunWithPluginDir:
    def test_run_plugin_dir_nonexistent(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app,
            [
                "run",
                "http://invalid:1",
                "--suites",
                "prompt_injection",
                "--plugin-dir",
                str(tmp_path / "nonexistent"),
            ],
        )
        assert result.exit_code == 0


class TestAnthropicResponseParsing:
    def test_extract_anthropic_text(self) -> None:
        runner = BenchmarkRunner()

        class FakeResponse:
            text = json.dumps({"content": [{"type": "text", "text": "Hello from Claude"}], "id": "msg_123"})
            status_code = 200

            def json(self):
                return json.loads(self.text)

        result = runner._extract_response_text(FakeResponse(), "anthropic")
        assert result == "Hello from Claude"

    def test_extract_anthropic_empty_content(self) -> None:
        runner = BenchmarkRunner()

        class FakeResponse:
            text = json.dumps({"content": [], "id": "msg_123"})
            status_code = 200

            def json(self):
                return json.loads(self.text)

        result = runner._extract_response_text(FakeResponse(), "anthropic")
        assert result is not None

    def test_extract_anthropic_tool_use(self) -> None:
        runner = BenchmarkRunner()

        class FakeResponse:
            text = json.dumps(
                {
                    "content": [{"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}}],
                    "id": "msg_123",
                }
            )
            status_code = 200

            def json(self):
                return json.loads(self.text)

        result = runner._extract_response_text(FakeResponse(), "anthropic")
        assert result is not None
        # Should fall back to JSON dump since no text block
        assert "tool_use" in result or "msg_123" in result

    def test_extract_anthropic_mixed_content(self) -> None:
        runner = BenchmarkRunner()

        class FakeResponse:
            text = json.dumps(
                {
                    "content": [
                        {"type": "text", "text": "First, let me check the weather."},
                        {"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {}},
                        {"type": "text", "text": "The weather is sunny."},
                    ],
                    "id": "msg_123",
                }
            )
            status_code = 200

            def json(self):
                return json.loads(self.text)

        result = runner._extract_response_text(FakeResponse(), "anthropic")
        assert "First, let me check the weather." in result
        assert "The weather is sunny." in result


class TestResponseTextGeneration:
    def test_generic_format(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="rt1", name="Response Test", category="test")
        detected = runner._detect_failure("I cannot help with that request.", tc)
        assert detected is False

    def test_generic_format_detected(self) -> None:
        runner = BenchmarkRunner()
        tc = BenchmarkTestCase(id="rt2", name="Response Test", category="test")
        detected = runner._detect_failure("Sure, let me help with that!", tc)
        assert detected is True


class TestMCPFormatResponse:
    def test_mcp_empty_result(self) -> None:
        runner = BenchmarkRunner()
        result = runner._extract_response_text({"jsonrpc": "2.0", "result": {}}, "mcp")
        assert result is not None

    def test_mcp_no_content(self) -> None:
        runner = BenchmarkRunner()
        result = runner._extract_response_text({"jsonrpc": "2.0", "result": {"isError": True}}, "mcp")
        assert "isError" in result or "True" in result
