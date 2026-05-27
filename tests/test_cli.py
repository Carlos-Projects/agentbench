"""Tests for CLI commands using Typer CliRunner."""

from pathlib import Path

from typer.testing import CliRunner

from agentbench.cli import app

runner = CliRunner()


class TestCLI:
    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "AgentBench v" in result.stdout

    def test_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "run" in result.stdout
        assert "suite" in result.stdout
        assert "compare" in result.stdout
        assert "leaderboard" in result.stdout
        assert "report" in result.stdout
        assert "trend" in result.stdout
        assert "store" in result.stdout

    def test_suite_list(self) -> None:
        result = runner.invoke(app, ["suite", "--list"])
        assert result.exit_code == 0
        assert "prompt_injection" in result.stdout
        assert "tool_poisoning" in result.stdout
        assert "ssrf" in result.stdout

    def test_suite_show(self) -> None:
        result = runner.invoke(app, ["suite", "--show", "prompt_injection"])
        assert result.exit_code == 0
        assert "pi-001" in result.stdout
        assert "Direct injection" in result.stdout

    def test_suite_show_invalid(self) -> None:
        result = runner.invoke(app, ["suite", "--show", "nonexistent"])
        assert result.exit_code != 0

    def test_report_convert_to_html(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "report.html"
        result = runner.invoke(app, ["report", str(demo), "--html", str(output)])
        assert result.exit_code == 0
        assert output.exists()
        content = output.read_text()
        assert "demo-agent" in content

    def test_report_convert_to_markdown(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output = tmp_path / "report.md"
        result = runner.invoke(app, ["report", str(demo), "--markdown", str(output)])
        assert result.exit_code == 0
        assert output.exists()

    def test_compare_reports(self) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        result = runner.invoke(app, ["compare", str(demo), str(demo)])
        assert result.exit_code == 0
        assert "Comparison" in result.stdout or "Score" in result.stdout

    def test_leaderboard_from_example(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output_dir = tmp_path / "lb"
        result = runner.invoke(app, ["leaderboard", str(demo), "--output", str(output_dir)])
        assert result.exit_code == 0
        assert (output_dir / "leaderboard.json").exists()

    def test_leaderboard_markdown(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        output_dir = tmp_path / "lb2"
        md_path = tmp_path / "LEADERBOARD.md"
        result = runner.invoke(app, ["leaderboard", str(demo), "--output", str(output_dir), "--markdown", str(md_path)])
        assert result.exit_code == 0
        assert md_path.exists()

    def test_trend_from_example(self) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        result = runner.invoke(app, ["trend", str(demo), str(demo)])
        assert result.exit_code == 0
        assert "Direction" in result.stdout or "Trend" in result.stdout

    def test_run_without_target_shows_error(self) -> None:
        result = runner.invoke(app, ["run"])
        assert result.exit_code != 0

    def test_run_invalid_target(self) -> None:
        result = runner.invoke(app, ["run", "http://invalid:1", "--suites", "prompt_injection"])
        assert result.exit_code == 0
        assert "prompt_injection" in result.stdout

    def test_store_save(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        db = tmp_path / "test.db"
        result = runner.invoke(app, ["store", "save", "--report", str(demo), "--db", str(db)])
        assert result.exit_code == 0
        assert "Saved" in result.stdout

    def test_store_list(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        db = tmp_path / "test2.db"
        runner.invoke(app, ["store", "save", "--report", str(demo), "--db", str(db)])
        result = runner.invoke(app, ["store", "list", "--db", str(db)])
        assert result.exit_code == 0
        assert "demo-agent" in result.stdout

    def test_store_get(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        db = tmp_path / "test3.db"
        runner.invoke(app, ["store", "save", "--report", str(demo), "--db", str(db)])
        result = runner.invoke(app, ["store", "get", "--id", "1", "--db", str(db)])
        assert result.exit_code == 0
        assert "demo-agent" in result.stdout

    def test_store_clean(self, tmp_path: Path) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        db = tmp_path / "test4.db"
        runner.invoke(app, ["store", "save", "--report", str(demo), "--db", str(db)])
        result = runner.invoke(app, ["store", "clean", "--keep", "0", "--db", str(db)])
        assert result.exit_code == 0

    def test_store_invalid_command(self, tmp_path: Path) -> None:
        db = tmp_path / "test5.db"
        result = runner.invoke(app, ["store", "invalid", "--db", str(db)])
        assert result.exit_code != 0

    def test_init_creates_config(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", str(tmp_path / "my-benchmark")])
        assert result.exit_code == 0
        assert (tmp_path / "my-benchmark" / "agentbench.yaml").exists()

    def test_validate_valid_report(self) -> None:
        demo = Path(__file__).parent.parent / "examples" / "demo_results.json"
        result = runner.invoke(app, ["validate", str(demo)])
        assert result.exit_code == 0

    def test_validate_invalid_report(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text('{"invalid": true}')
        result = runner.invoke(app, ["validate", str(bad)])
        assert result.exit_code != 0

    def test_validate_missing_file(self) -> None:
        result = runner.invoke(app, ["validate", "/nonexistent/file.json"])
        assert result.exit_code != 0

    def test_init_with_config(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["init", str(tmp_path / "bench2"), "--target", "http://test:8080"])
        assert result.exit_code == 0
        config = (tmp_path / "bench2" / "agentbench.yaml").read_text()
        assert "http://test:8080" in config
