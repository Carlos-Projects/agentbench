"""Smoke test: build, install, and verify the package works end-to-end."""

import subprocess
import sys
from pathlib import Path

import pytest


class TestSmoke:
    def test_package_importable(self) -> None:
        import agentbench  # noqa: F401
        from agentbench import __version__

        assert __version__ is not None

    def test_cli_help(self) -> None:
        from typer.testing import CliRunner

        from agentbench.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.stdout
        assert "info" in result.stdout
        assert "init" in result.stdout
        assert "validate" in result.stdout

    def test_info_command(self) -> None:
        from typer.testing import CliRunner

        from agentbench.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "AgentBench" in result.stdout
        assert "Python" in result.stdout

    def test_taxonomy_importable(self) -> None:
        from agentbench.taxonomy import (
            benchmark_result_to_taxonomy,
            report_to_taxonomy_events,
        )

        assert callable(benchmark_result_to_taxonomy)
        assert callable(report_to_taxonomy_events)

    def test_taxonomy_converts_result(self) -> None:
        from agentbench.models import BenchmarkResult, BenchmarkTestCase, TestStatus
        from agentbench.taxonomy import benchmark_result_to_taxonomy

        tc = BenchmarkTestCase(id="t1", name="Test", category="prompt_injection", description="Test desc")
        result = BenchmarkResult(test_case=tc, status=TestStatus.FAILED, detected=True, response="vulnerable")
        event = benchmark_result_to_taxonomy(result)
        assert event.source == "agentbench"
        assert event.attack_category is not None
        assert event.blocked is True

    @pytest.mark.slow
    def test_build_and_install(self) -> None:
        """Build the package and install it in isolation."""
        project_root = Path(__file__).parent.parent

        result = subprocess.run(
            [sys.executable, "-m", "build", "--no-isolation"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )
        assert result.returncode == 0, f"Build failed: {result.stderr}"

        whl = list((project_root / "dist").glob("*.whl"))
        assert len(whl) >= 1

        install_result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--force-reinstall", str(whl[0])],
            capture_output=True,
            text=True,
        )
        assert install_result.returncode == 0, f"Install failed: {install_result.stderr}"

        version_result = subprocess.run(
            [sys.executable, "-m", "agentbench", "--version"],
            capture_output=True,
            text=True,
        )
        assert version_result.returncode == 0
        assert "AgentBench v" in version_result.stdout
