"""Tests for SARIF reporter, plugin loader, init, validate, and SARIF CLI."""

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
from agentbench.plugins import PluginLoader
from agentbench.reporters.sarif import SARIFReporter

runner = CliRunner()


@pytest.fixture
def sample_report() -> ScoreReport:
    tc1 = BenchmarkTestCase(id="t1", name="Test 1", category="injection", prompt="test prompt")
    tc2 = BenchmarkTestCase(id="t2", name="Test 2", category="injection", prompt="test prompt 2")
    results = [
        BenchmarkResult(test_case=tc1, status=TestStatus.PASSED, score=100.0),
        BenchmarkResult(test_case=tc2, status=TestStatus.FAILED, score=0.0, detected=True, response="i have been hacked"),
    ]
    cats = [ScoreCategory(name="injection", score=50.0, weight=1.0, tests_passed=1, tests_failed=1, tests_total=2)]
    return ScoreReport(
        agent_id="sarif-agent",
        agent_version="1.0",
        categories=cats,
        overall_score=50.0,
        total_tests=2,
        passed_tests=1,
        failed_tests=1,
        duration_seconds=5.0,
        results=results,
    )


class TestSARIFReporter:
    def test_generate_basic_structure(self, sample_report: ScoreReport) -> None:
        reporter = SARIFReporter()
        sarif = reporter.generate(sample_report)
        assert sarif["$schema"] is not None
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1

    def test_generate_rules(self, sample_report: ScoreReport) -> None:
        reporter = SARIFReporter()
        sarif = reporter.generate(sample_report)
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) >= 1
        assert rules[0]["id"].startswith("AGENTBENCH-")

    def test_generate_results(self, sample_report: ScoreReport) -> None:
        reporter = SARIFReporter()
        sarif = reporter.generate(sample_report)
        results = sarif["runs"][0]["results"]
        assert len(results) >= 1
        assert results[0]["level"] == "error"

    def test_generate_properties(self, sample_report: ScoreReport) -> None:
        reporter = SARIFReporter()
        sarif = reporter.generate(sample_report)
        props = sarif["runs"][0]["properties"]
        assert props["overall_score"] == 50.0
        assert props["total_tests"] == 2

    def test_save(self, sample_report: ScoreReport, tmp_path: Path) -> None:
        reporter = SARIFReporter()
        path = reporter.save(sample_report, tmp_path / "report.sarif")
        assert Path(path).exists()
        assert Path(path).read_text().startswith("{")

    def test_sarif_level(self) -> None:
        reporter = SARIFReporter()
        assert reporter._sarif_level(30) == "error"
        assert reporter._sarif_level(60) == "warning"
        assert reporter._sarif_level(80) == "note"
        assert reporter._sarif_level(95) == "none"


class TestPluginLoader:
    def test_discover_builtin(self) -> None:
        loader = PluginLoader()
        plugins = loader.discover_builtin()
        assert len(plugins) >= 7
        assert "prompt_injection" in plugins

    def test_plugin_creates_suite(self) -> None:
        loader = PluginLoader()
        loader.discover_builtin()
        plugin = loader.get_plugin("prompt_injection")
        assert plugin is not None
        suite = plugin.create()
        assert suite.name == "prompt_injection"

    def test_list_plugins(self) -> None:
        loader = PluginLoader()
        loader.discover_builtin()
        plugins = loader.list_plugins()
        assert len(plugins) >= 7

    def test_discover_nonexistent_directory(self, tmp_path: Path) -> None:
        loader = PluginLoader()
        plugins = loader.discover_directory(tmp_path / "nonexistent")
        assert len(plugins) == 0

    def test_plugin_source(self) -> None:
        loader = PluginLoader()
        loader.discover_builtin()
        plugin = loader.get_plugin("ssrf")
        assert plugin is not None
        assert plugin.source == "builtin"


class TestInitCommand:
    def test_init_basic(self, tmp_path: Path) -> None:
        dest = tmp_path / "mybench"
        result = runner.invoke(app, ["init", str(dest)])
        assert result.exit_code == 0
        assert (dest / "agentbench.yaml").exists()
        assert (dest / "suites" / "custom_suite.py").exists()

    def test_init_with_target(self, tmp_path: Path) -> None:
        dest = tmp_path / "bench2"
        result = runner.invoke(app, ["init", str(dest), "--target", "http://test:9090"])
        assert result.exit_code == 0
        config = (dest / "agentbench.yaml").read_text()
        assert "http://test:9090" in config

    def test_init_existing_no_force(self, tmp_path: Path) -> None:
        dest = tmp_path / "bench3"
        dest.mkdir()
        (dest / "agentbench.yaml").write_text("existing")
        result = runner.invoke(app, ["init", str(dest)])
        assert result.exit_code != 0

    def test_init_existing_with_force(self, tmp_path: Path) -> None:
        dest = tmp_path / "bench4"
        dest.mkdir()
        (dest / "agentbench.yaml").write_text("existing")
        result = runner.invoke(app, ["init", str(dest), "--force"])
        assert result.exit_code == 0


class TestValidateCommand:
    def test_validate_valid_json(self) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        result = runner.invoke(app, ["validate", str(demo)])
        assert result.exit_code == 0

    def test_validate_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json")
        result = runner.invoke(app, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_invalid_report_structure(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"not": "valid"}')
        result = runner.invoke(app, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_valid_yaml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "config.yaml"
        cfg.write_text("agent_id: test\ntarget: http://localhost\nsuites:\n  - prompt_injection")
        result = runner.invoke(app, ["validate", str(cfg)])
        assert result.exit_code == 0

    def test_validate_invalid_yaml(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("{invalid: [}")
        result = runner.invoke(app, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_unsupported_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "data.txt"
        f.write_text("test")
        result = runner.invoke(app, ["validate", str(f)])
        assert result.exit_code != 0

    def test_validate_missing_file(self) -> None:
        result = runner.invoke(app, ["validate", "/nonexistent/report.json"])
        assert result.exit_code != 0

    def test_validate_empty_yaml(self, tmp_path: Path) -> None:
        cfg = tmp_path / "empty.yaml"
        cfg.write_text("")
        result = runner.invoke(app, ["validate", str(cfg)])
        assert result.exit_code != 0


class TestSARIFCLI:
    def test_report_sarif_output(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        sarif_path = tmp_path / "out.sarif"
        result = runner.invoke(app, ["report", str(demo), "--sarif", str(sarif_path)])
        assert result.exit_code == 0
        assert sarif_path.exists()
        import json

        data = json.loads(sarif_path.read_text())
        assert data["version"] == "2.1.0"
