"""Tests for remaining untested modules: retry, webhooks, JSON logging, __main__."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentbench.cli import app
from agentbench.models import (
    BenchmarkResult,
    BenchmarkTestCase,
    ScoreCategory,
    ScoreReport,
    TestStatus,
)
from agentbench.utils.retry import retry_async
from agentbench.webhooks import WebhookNotifier

runner = CliRunner()


@pytest.fixture
def sample_report() -> ScoreReport:
    tc = BenchmarkTestCase(id="t1", name="Test", category="test", prompt="hello")
    result = BenchmarkResult(test_case=tc, status=TestStatus.PASSED, score=100.0)
    cat = ScoreCategory(name="test", score=100.0, tests_total=1, tests_passed=1)
    return ScoreReport(
        agent_id="test-agent",
        categories=[cat],
        overall_score=100.0,
        total_tests=1,
        passed_tests=1,
        results=[result],
    )


@pytest.mark.asyncio
async def test_retry_async_success() -> None:
    call_count = 0

    async def succeed() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await retry_async(succeed, max_retries=3)
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_failure_then_success() -> None:
    call_count = 0

    async def fail_then_succeed() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("fail")
        return "ok"

    result = await retry_async(fail_then_succeed, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_all_fail() -> None:
    call_count = 0

    async def always_fail() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("always fail")

    with pytest.raises(ValueError, match="always fail"):
        await retry_async(always_fail, max_retries=2, base_delay=0.01)
    assert call_count == 2


class TestWebhookNotifier:
    @pytest.mark.asyncio
    async def test_send_no_url(self, sample_report) -> None:
        notifier = WebhookNotifier(url="")
        result = await notifier.send(sample_report)
        assert result is False

    def test_validate_url_empty(self) -> None:
        notifier = WebhookNotifier(url="")
        assert notifier.validate_url() is False

    def test_validate_url_valid(self) -> None:
        notifier = WebhookNotifier(url="https://hooks.example.com/benchmark")
        assert notifier.validate_url() is True

    def test_validate_url_invalid(self) -> None:
        notifier = WebhookNotifier(url="not-a-url")
        assert notifier.validate_url() is False


class TestCLICompletion:
    def test_completion_bash(self) -> None:
        result = runner.invoke(app, ["completion", "bash"])
        assert result.exit_code == 0
        assert "COMPLETE" in result.stdout or "source_bash" in result.stdout or "install-completion" in result.stdout

    def test_completion_zsh(self) -> None:
        result = runner.invoke(app, ["completion", "zsh"])
        assert result.exit_code == 0


class TestCLIExport:
    def test_export_no_format(self) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        result = runner.invoke(app, ["export", str(demo)])
        assert result.exit_code == 0
        assert "no export format" in result.stdout.lower()

    def test_export_sarif(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "out.sarif"
        result = runner.invoke(app, ["export", str(demo), "--sarif", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["version"] == "2.1.0"

    def test_export_mcpguard(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "policy.yaml"
        result = runner.invoke(app, ["export", str(demo), "--mcpguard", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_export_mcpscop(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "events.json"
        result = runner.invoke(app, ["export", str(demo), "--mcpscop", str(output)])
        assert result.exit_code == 0
        assert output.exists()


class TestCLIConfig:
    def test_config_create(self, tmp_path: Path) -> None:
        cfg = tmp_path / "bench.yaml"
        result = runner.invoke(app, ["config", "create", "--file", str(cfg), "--target", "http://test:8080"])
        assert result.exit_code == 0
        assert cfg.exists()
        assert "http://test:8080" in cfg.read_text()

    def test_config_show(self, tmp_path: Path) -> None:
        cfg = tmp_path / "show.yaml"
        cfg.write_text("agent_id: test-agent\ntarget: http://localhost")
        result = runner.invoke(app, ["config", "show", "--file", str(cfg)])
        assert result.exit_code == 0
        assert "test-agent" in result.stdout

    def test_config_show_missing(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["config", "show", "--file", str(tmp_path / "nonexistent.yaml")])
        assert result.exit_code != 0

    def test_config_validate(self, tmp_path: Path) -> None:
        cfg = tmp_path / "valid.yaml"
        cfg.write_text("agent_id: test\ntarget: http://localhost\nsuites:\n  - prompt_injection")
        result = runner.invoke(app, ["config", "validate", "--file", str(cfg)])
        assert result.exit_code == 0

    def test_config_create_existing(self, tmp_path: Path) -> None:
        cfg = tmp_path / "existing.yaml"
        cfg.write_text("old")
        result = runner.invoke(app, ["config", "create", "--file", str(cfg)])
        assert result.exit_code != 0

    def test_config_invalid_action(self) -> None:
        result = runner.invoke(app, ["config", "invalid"])
        assert result.exit_code != 0


class TestMain:
    def test_main_module_importable(self) -> None:
        from agentbench import __main__  # noqa: F401

    def test_python_m_run(self) -> None:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-m", "agentbench", "--version"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "AgentBench v" in result.stdout
