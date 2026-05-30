"""AgentBench CLI using Typer."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console

from agentbench import __version__
from agentbench.comparison.analyzer import ComparisonAnalyzer
from agentbench.comparison.trend import TrendAnalyzer
from agentbench.leaderboard.generator import LeaderboardGenerator
from agentbench.leaderboard.publisher import LeaderboardPublisher
from agentbench.models import ScoreReport
from agentbench.reporters.console import ConsoleReporter
from agentbench.reporters.html import HTMLReporter
from agentbench.reporters.json import JSONReporter
from agentbench.reporters.markdown import MarkdownReporter
from agentbench.runner import BenchmarkRunner
from agentbench.suites import SUITE_REGISTRY, get_suite_names

app = typer.Typer(
    name="agentbench",
    help="Automated benchmarking framework for evaluating AI agent security",
    no_args_is_help=True,
)
console = Console()
console_reporter = ConsoleReporter()


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"AgentBench v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version", callback=_version_callback),
) -> None:
    """AgentBench - AI Agent Security Benchmarking Framework."""


@app.command()
def run(
    target: str = typer.Argument(..., help="Target agent URL"),
    suites: str = typer.Option("all", "--suites", "-s", help="Comma-separated suite names or 'all'"),
    agent_id: str = typer.Option("unknown", "--agent-id", "-a", help="Agent identifier"),
    agent_version: str = typer.Option("", "--agent-version", "-v", help="Agent version"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output report file (JSON)"),
    html: str | None = typer.Option(None, "--html", help="Output HTML report file"),
    markdown: str | None = typer.Option(None, "--markdown", "-m", help="Output Markdown report file"),
    timeout: float = typer.Option(30.0, "--timeout", "-t", help="Request timeout in seconds"),
    header: list[str] = typer.Option([], "--header", "-H", help="Additional HTTP headers"),
    api_format: str = typer.Option("generic", "--api-format", "-f", help="API format: generic, openai, or mcp"),
    seed: int | None = typer.Option(None, "--seed", help="Random seed for reproducibility"),
    config: str | None = typer.Option(None, "--config", "-c", help="YAML config file path"),
    rate_limit: float = typer.Option(0.0, "--rate-limit", "-r", help="Minimum delay (s) between requests"),
    parallel: int = typer.Option(1, "--parallel", "-p", help="Parallel test execution count"),
    exit_below: float | None = typer.Option(None, "--exit-below", help="Exit with code 1 if overall score below this threshold"),
    mcpguard: str | None = typer.Option(None, "--mcpguard", help="Generate MCPGuard policy YAML file"),
    mcpscop: str | None = typer.Option(None, "--mcpscop", help="Generate MCPscop-compatible events JSON file"),
    sarif: str | None = typer.Option(None, "--sarif", help="Generate SARIF report file"),
    store: bool = typer.Option(False, "--store", help="Save results to SQLite store"),
    db: str = typer.Option("agentbench.db", "--db", help="SQLite database path for --store"),
    plugin_dir: str | None = typer.Option(None, "--plugin-dir", help="Directory with custom suite plugins"),
    webhook: str | None = typer.Option(None, "--webhook", help="URL for completion webhook"),
    webhook_secret: str | None = typer.Option(None, "--webhook-secret", help="Secret for webhook auth"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output (DEBUG logging)"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Quiet mode (WARNING logging only)"),
    retry: int = typer.Option(0, "--retry", help="Retry failed requests N times"),
    log_format: str = typer.Option("text", "--log-format", help="Log format: text or json"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show tests that would run without executing"),
    exclude_suites: str = typer.Option("", "--exclude-suites", "-x", help="Comma-separated suite names to exclude"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags to filter (e.g., 'injection,critical')"),
) -> None:
    """Run benchmark suites against a target agent.

    Executes one or more benchmark suites against a target AI agent,
    collects results, and generates reports in various formats.

    Args:
        target: Target agent URL.
        suites: Comma-separated suite names or "all".
        agent_id: Agent identifier.
        agent_version: Agent version string.
        output: Path to JSON report output file.
        html: Path to HTML report output file.
        markdown: Path to Markdown report output file.
        timeout: Request timeout in seconds.
        header: Additional HTTP headers.
        api_format: API format (generic, openai, or mcp).
        seed: Random seed for reproducibility.
        config: Path to YAML configuration file.
        rate_limit: Minimum delay between requests.
        parallel: Number of parallel test executions.
        exit_below: Exit if score falls below this threshold.
        mcpguard: Output path for MCPGuard policy file.
        mcpscop: Output path for MCPscop events file.
        sarif: Output path for SARIF report file.
        store: Whether to save results to the SQLite store.
        db: SQLite database path.
        plugin_dir: Directory containing custom plugins.
        webhook: Completion webhook URL.
        webhook_secret: Secret used for webhook authentication.
        verbose: Enable verbose logging.
        quiet: Enable quiet logging.
        retry: Number of retries for failed requests.
        log_format: Logging format.
        dry_run: Show tests without executing them.
        exclude_suites: Comma-separated suites to exclude.
        tags: Comma-separated tag filters.

    Returns:
        None

    Raises:
        typer.Exit: If the benchmark score falls below the
            configured threshold.
    """
    import random

    from rich.progress import (
        BarColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
    )

    from agentbench.logger import logger as bench_logger

    if seed is not None:
        random.seed(seed)
        bench_logger.info("Using random seed: %d", seed)

    if config is not None:
        cfg = _load_config(config)
        target = cfg.get("target", target)
        suites = ",".join(cfg.get("suites", [])) if cfg.get("suites") else suites
        agent_id = cfg.get("agent_id", agent_id)
        agent_version = cfg.get("agent_version", agent_version)
        timeout = cfg.get("timeout", timeout)
        api_format = cfg.get("api_format", api_format)
        rate_limit = cfg.get("rate_limit", rate_limit)
        parallel = cfg.get("parallel", parallel)
        if cfg.get("seed") is not None:
            seed = cfg["seed"]
        for k, v in cfg.get("headers", {}).items():
            header.append(f"{k}: {v}")

    if verbose:
        bench_logger.setLevel("DEBUG")
    elif quiet:
        bench_logger.setLevel("WARNING")
    else:
        bench_logger.setLevel("DEBUG" if api_format == "debug" else "INFO")

    if log_format == "json":
        from agentbench.utils.logging_json import setup_json_logger

        bench_logger = setup_json_logger()

    headers = _parse_headers(header)

    selected_suites = _resolve_suites(suites)
    suite_instances = [cls().build_suite() for cls in selected_suites]

    if exclude_suites:
        excluded = {s.strip() for s in exclude_suites.split(",")}
        suite_instances = [s for s in suite_instances if s.name not in excluded]
        if excluded - {s.name for s in suite_instances}:
            for name in sorted(excluded - {s.name for s in suite_instances}):
                rprint(f"[yellow]Warning: excluded suite '{name}' not found[/yellow]")

    if tags:
        tag_filter = {t.strip() for t in tags.split(",")}
        for suite in suite_instances:
            suite.test_cases = [tc for tc in suite.test_cases if tag_filter & set(tc.tags)]
        suite_instances = [s for s in suite_instances if s.test_cases]

    if dry_run:
        rprint("\n[bold]Dry run — tests that would execute:[/bold]")
        for s in suite_instances:
            rprint(f"\n[cyan]{s.name}[/cyan] ({len(s.test_cases)} tests):")
            for tc in s.test_cases:
                tags_str = f" [{','.join(tc.tags)}]" if tc.tags else ""
                rprint(f"  [dim]{tc.id}[/dim] {tc.name}{tags_str}")
        return

    if plugin_dir:
        from agentbench.plugins import PluginLoader

        loader = PluginLoader()
        loader.discover_directory(plugin_dir)
        for plugin in loader.list_plugins():
            if plugin.source.startswith("file:"):
                cls = plugin.cls
                suite_instances.append(cls().build_suite())
                rprint(f"  Loaded plugin: [green]{plugin.name}[/green] from {plugin.source}")

    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    )

    total_tests = sum(len(s.test_cases) for s in suite_instances)
    task_id = progress.add_task("Running benchmarks...", total=total_tests)

    def on_progress(name: str, current: int, total: int) -> None:
        progress.update(task_id, completed=current, description=f"Testing: {name[:40]:40s}")

    runner = BenchmarkRunner(
        headers=headers,
        timeout=timeout,
        api_format=api_format,
        rate_limit=rate_limit,
        progress_callback=on_progress,
        parallel=parallel,
        retry_count=retry,
    )

    rprint(f"[bold cyan]AgentBench[/bold cyan] v{__version__}")
    rprint(f"Target: [yellow]{target}[/yellow]")
    rprint(f"Suites: {', '.join(s.name for s in suite_instances)} ({total_tests} tests)")
    if seed is not None:
        rprint(f"Seed: {seed}")

    if not dry_run:
        _validate_target(target, api_format, timeout)

    with progress:
        report = asyncio.run(
            runner.run_suites(
                suites=suite_instances,
                agent_id=agent_id,
                agent_version=agent_version,
                target_url=target,
            )
        )

    console_reporter.print_report(report)

    if output:
        json_reporter = JSONReporter()
        path = json_reporter.save(report, output)
        rprint(f"\n[green]JSON report saved:[/green] {path}")

    if html:
        html_reporter = HTMLReporter()
        path = html_reporter.save(report, html)
        rprint(f"[green]HTML report saved:[/green] {path}")

    if markdown:
        md_reporter = MarkdownReporter()
        path = md_reporter.save(report, markdown)
        rprint(f"[green]Markdown report saved:[/green] {path}")

    if mcpguard:
        from agentbench.integrations.mcpguard import MCPGuardPolicyGenerator

        gen = MCPGuardPolicyGenerator()
        path = gen.save_yaml(report, mcpguard)
        rprint(f"[green]MCPGuard policy saved:[/green] {path}")

    if store:
        from agentbench.store import BenchmarkStore

        store_inst = BenchmarkStore(db_path=db)
        run_id = store_inst.save(report)
        rprint(f"[green]Saved to store: run #{run_id}[/green]")

    if webhook:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_send_webhook(webhook, webhook_secret or "", report))
            else:
                asyncio.run(_send_webhook(webhook, webhook_secret or "", report))
        except RuntimeError:
            _send_webhook_sync(webhook, webhook_secret or "", report)

    if mcpscop:
        from agentbench.integrations.mcpscop import MCPscopExporter

        exporter = MCPscopExporter()
        path = exporter.save_events_json(report, mcpscop)
        rprint(f"[green]MCPscop events saved:[/green] {path}")

    if sarif:
        from agentbench.reporters.sarif import SARIFReporter

        sarif_reporter = SARIFReporter()
        path = sarif_reporter.save(report, sarif)
        rprint(f"[green]SARIF report saved:[/green] {path}")

    if exit_below is not None and report.overall_score < exit_below:
        rprint(f"\n[red]CI FAILURE: Score {report.overall_score:.1f} is below threshold {exit_below}[/red]")
        raise typer.Exit(code=1)


@app.command()
def init(
    path: str = typer.Argument(".", help="Directory to create the benchmark project in"),
    target: str = typer.Option("http://localhost:8080", "--target", "-t", help="Default target URL"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files"),
) -> None:
    """Scaffold a new AgentBench benchmark project.

    Creates a benchmark project directory with a default
    configuration file and example custom suite template.

    Args:
        path: Directory where the benchmark project will be created.
        target: Default target URL to include in the generated
            configuration file.
        force: Whether to overwrite existing files.

    Returns:
        None

    Raises:
        typer.Exit: If the configuration file already exists and
            force is not enabled.
    """
    from pathlib import Path as _Path

    dest = _Path(path)
    dest.mkdir(parents=True, exist_ok=True)

    config_path = dest / "agentbench.yaml"
    if config_path.exists() and not force:
        rprint(f"[red]File exists: {config_path}. Use --force to overwrite.[/red]")
        raise typer.Exit(code=1)

    config_content = f"""# AgentBench benchmark configuration
agent_id: my-agent
agent_version: "1.0.0"
target: {target}
timeout: 30.0
api_format: generic
suites:
  - prompt_injection
  - tool_poisoning
  - ssrf
  - data_exfiltration
  - jailbreak
  - memory_attacks
  - multi_agent
"""
    config_path.write_text(config_content)
    rprint(f"[green]Created:[/green] {config_path}")

    custom_suites = dest / "suites"
    custom_suites.mkdir(exist_ok=True)
    (custom_suites / "__init__.py").write_text("")
    example_suite = custom_suites / "custom_suite.py"
    if not example_suite.exists():
        example_suite.write_text(
            '''"""Example custom benchmark suite."""

from agentbench.suites.base import BaseSuite
from agentbench.models import BenchmarkTestCase, Severity


class CustomSuite(BaseSuite):
    """My custom benchmark suite."""

    name = "custom"
    category = "custom"
    description = "Custom security tests"
    failure_indicators = ["custom_indicator"]

    def generate_cases(self) -> list[BenchmarkTestCase]:
        return [
            BenchmarkTestCase(
                id="cu-001",
                name="Custom test",
                category=self.category,
                description="A custom security test",
                severity=Severity.MEDIUM,
                prompt="Test prompt here",
                expected_behavior="Expected behavior",
                tags=["custom"],
                weight=1.0,
            ),
        ]
'''
        )
        rprint(f"[green]Created:[/green] {example_suite}")

    rprint("\n[bold]Next steps:[/bold]")
    rprint(f"  1. Edit {config_path}")
    rprint(f"  2. Add custom suites in {custom_suites}")
    rprint(f"  3. Run: agentbench run --config {config_path}")


@app.command()
def validate(
    file: str = typer.Argument(..., help="Report JSON or config YAML file to validate"),
) -> None:
    """Validate a benchmark report or configuration file.

    Checks whether a benchmark report (JSON) or configuration
    file (YAML) is valid and displays summary information when
    validation succeeds.

    Args:
        file: Path to the report JSON or configuration YAML file
            to validate.

    Returns:
        None

    Raises:
        typer.Exit: If the file does not exist, contains invalid
            JSON or YAML, or has an unsupported file extension.
    """
    path = Path(file)
    if not path.exists():
        rprint(f"[red]File not found: {file}[/red]")
        raise typer.Exit(code=1)

    content = path.read_text()
    ext = path.suffix.lower()

    if ext == ".json":
        try:
            data = json.loads(content)
            _load_report(file)
            rprint(f"[green]Valid JSON report:[/green] {file}")
            agent = data.get("agent_id", "unknown")
            score = data.get("overall_score", 0)
            rprint(f"  Agent: {agent} | Score: {score}/100 | Tests: {data.get('total_tests', 0)}")
        except (json.JSONDecodeError, ValueError) as exc:
            rprint(f"[red]Invalid report: {exc}[/red]")
            raise typer.Exit(code=1)

    elif ext in (".yaml", ".yml"):
        try:
            import yaml

            cfg = yaml.safe_load(content)
            if not isinstance(cfg, dict):
                rprint("[red]Invalid YAML: must be a dictionary[/red]")
                raise typer.Exit(code=1)
            rprint(f"[green]Valid YAML config:[/green] {file}")
            for key in ("agent_id", "target", "suites"):
                if key in cfg:
                    rprint(f"  {key}: {cfg[key]}")
        except yaml.YAMLError as exc:
            rprint(f"[red]Invalid YAML: {exc}[/red]")
            raise typer.Exit(code=1)
    else:
        rprint(f"[red]Unsupported file type: {ext}. Use .json, .yaml, or .yml[/red]")
        raise typer.Exit(code=1)


@app.command()
def info() -> None:
    """Show system information and installed suite details.

    Displays AgentBench version information, Python and platform
    details, available benchmark suites, test case counts, and
    supported output and API formats.

    Returns:
        None
    """
    import platform
    import sys

    rprint(f"[bold]AgentBench[/bold] v{__version__}")
    rprint(f"  Python: {sys.version}")
    rprint(f"  Platform: {platform.platform()}")
    rprint(f"  Hostname: {platform.node()}")

    total_cases = 0
    for name in get_suite_names():
        cls = SUITE_REGISTRY[name]
        instance = cls()
        n = len(instance.generate_cases())
        total_cases += n

    rprint(f"\n[bold]Suites:[/bold] {len(get_suite_names())} built-in")
    rprint(f"  Test cases: {total_cases}")
    rprint("  Coverage by category:")
    for name in get_suite_names():
        cls = SUITE_REGISTRY[name]
        instance = cls()
        n = len(instance.generate_cases())
        rprint(f"    [cyan]{name}[/cyan]: {n} tests")

    rprint("\n[bold]Output formats:[/bold] console, JSON, HTML, Markdown, SARIF, MCPGuard, MCPscop")
    rprint("[bold]API formats:[/bold] generic, openai, anthropic, mcp")
    rprint("[bold]Data store:[/bold] SQLite (agentbench.db)")


@app.command()
def suite(
    list_suites: bool = typer.Option(False, "--list", "-l", help="List available suites"),
    show: str | None = typer.Option(None, "--show", "-s", help="Show test cases in a suite"),
) -> None:
    """List and inspect benchmark suites.

    Displays available benchmark suites and their metadata, or
    shows detailed information and test cases for a specific
    suite.

    Args:
        list_suites: Whether to display all available benchmark
            suites.
        show: Name of a specific suite to inspect.

    Returns:
        None

    Raises:
        typer.Exit: If the requested suite does not exist.
    """
    if list_suites:
        rprint("\n[bold]Available Benchmark Suites:[/bold]\n")
        for name in get_suite_names():
            cls = SUITE_REGISTRY[name]
            instance = cls()
            rprint(f"  [cyan]{name}[/cyan]")
            rprint(f"    {instance.description}")
            suite_obj = instance.build_suite()
            rprint(f"    Test cases: {len(suite_obj.test_cases)}\n")

    if show:
        if show not in SUITE_REGISTRY:
            rprint(f"[red]Unknown suite: {show}[/red]")
            rprint(f"Available: {', '.join(get_suite_names())}")
            raise typer.Exit(code=1)

        cls = SUITE_REGISTRY[show]
        instance = cls()
        suite_obj = instance.build_suite()

        rprint(f"\n[bold]Suite: {show}[/bold]")
        rprint(f"  {instance.description}")
        if instance.failure_indicators:
            indicators = ", ".join(instance.failure_indicators)
            rprint(f"  Failure indicators: [yellow]{indicators}[/yellow]")
        rprint()

        for tc in suite_obj.test_cases:
            severity_colors = {
                "critical": "red",
                "high": "yellow",
                "medium": "cyan",
                "low": "green",
                "info": "blue",
            }
            color = severity_colors.get(tc.severity.value, "white")
            rprint(f"  [{color}]{tc.id}[/{color}] {tc.name}")
            rprint(f"    Severity: {tc.severity.value} | Weight: {tc.weight}")
            rprint(f"    {tc.description}")
            rprint()


@app.command()
def compare(
    baseline: str = typer.Argument(..., help="Baseline JSON report file or store run ID"),
    target: str = typer.Argument(..., help="Target JSON report file or store run ID"),
    db: str = typer.Option("agentbench.db", "--db", help="SQLite database path (for store comparisons)"),
) -> None:
    """Compare two benchmark reports.

    Loads two benchmark reports and analyzes differences in
    security scores, regressions, and improvements between
    the baseline and target results.

    Args:
        baseline: Baseline report file path or stored run ID.
        target: Target report file path or stored run ID.
        db: SQLite database path used when comparing stored runs.

    Returns:
        None
    """
    baseline_report = _resolve_report_arg(baseline, db)
    target_report = _resolve_report_arg(target, db)

    analyzer = ComparisonAnalyzer()
    result = analyzer.compare(baseline_report, target_report)

    console_reporter.print_comparison(baseline_report, target_report)

    rprint(f"\n[bold]Regressions:[/bold] {result.regression_count}")
    rprint(f"[bold]Improvements:[/bold] {result.improvement_count}")

    if result.regression_count > 0:
        regressions = analyzer.find_regressions(baseline_report, target_report)
        for cat, delta in regressions:
            rprint(f"  [red]! {cat}: {delta:+.1f}[/red]")


@app.command()
def leaderboard(
    reports: list[str] = typer.Argument(..., help="JSON report files"),
    output: str = typer.Option("leaderboard", "--output", "-o", help="Output directory"),
    markdown_output: str | None = typer.Option(None, "--markdown", "-m", help="Markdown output file"),
) -> None:
    """Generate a leaderboard from multiple benchmark reports.

    Loads benchmark reports, generates ranked leaderboard
    entries, and publishes leaderboard data in JSON and
    optionally Markdown format.

    Args:
        reports: Paths to benchmark report JSON files.
        output: Output directory for generated leaderboard files.
        markdown_output: Optional Markdown output file name.

    Returns:
        None
    """
    loaded_reports = [_load_report(r) for r in reports]
    generator = LeaderboardGenerator()
    entries = generator.generate(loaded_reports)

    publisher = LeaderboardPublisher(output_dir=output)
    json_path = publisher.publish_json(loaded_reports)
    rprint(f"[green]Leaderboard JSON:[/green] {json_path}")

    if markdown_output:
        md_path = publisher.publish_markdown(loaded_reports, filename=markdown_output)
        rprint(f"[green]Leaderboard Markdown:[/green] {md_path}")

    rprint("\n[bold]Leaderboard:[/bold]\n")
    rprint(f"{'Rank':<6} {'Agent':<20} {'Version':<12} {'Score':<8} {'Passed':<8}")
    rprint("-" * 54)
    for e in entries:
        rprint(f"{e.rank:<6} {e.agent_id:<20} {e.agent_version:<12} {e.overall_score:<8.1f} {e.passed_tests}/{e.total_tests}")


@app.command()
def report(
    input_file: str = typer.Argument(..., help="JSON report file to convert"),
    html: str | None = typer.Option(None, "--html", help="Output HTML file"),
    markdown: str | None = typer.Option(None, "--markdown", "-m", help="Output Markdown file"),
    sarif: str | None = typer.Option(None, "--sarif", help="Output SARIF file"),
) -> None:
    """Convert a benchmark report to different output formats.

    Loads a benchmark report and generates additional output
    formats such as HTML, Markdown, or SARIF while displaying
    the report summary in the console.

    Args:
        input_file: Path to the benchmark report JSON file.
        html: Output path for the generated HTML report.
        markdown: Output path for the generated Markdown report.
        sarif: Output path for the generated SARIF report.

    Returns:
        None
    """
    report_data = _load_report(input_file)
    console_reporter.print_report(report_data)

    if html:
        html_reporter = HTMLReporter()
        path = html_reporter.save(report_data, html)
        rprint(f"\n[green]HTML report saved:[/green] {path}")

    if markdown:
        md_reporter = MarkdownReporter()
        path = md_reporter.save(report_data, markdown)
        rprint(f"[green]Markdown report saved:[/green] {path}")

    if sarif:
        from agentbench.reporters.sarif import SARIFReporter

        sarif_reporter = SARIFReporter()
        path = sarif_reporter.save(report_data, sarif)
        rprint(f"[green]SARIF report saved:[/green] {path}")


@app.command()
def trend(
    reports: list[str] = typer.Argument(default=None, help="Chronological JSON report files"),
    agent_id: str | None = typer.Option(None, "--agent-id", "-a", help="Agent ID (for store-based trend)"),
    db: str = typer.Option("agentbench.db", "--db", help="SQLite database path"),
    from_store: bool = typer.Option(False, "--from-store", help="Load reports from SQLite store"),
) -> None:
    """Analyze security trends across benchmark reports.

    Builds and displays historical performance trends from a
    series of benchmark reports or stored benchmark runs,
    including trend direction, volatility, moving averages,
    and estimated future scores.

    Args:
        reports: Chronological benchmark report JSON files.
        agent_id: Agent identifier used when loading reports
            from the SQLite store.
        db: Path to the SQLite database.
        from_store: Whether to load historical runs from the
            benchmark store instead of report files.

    Returns:
        None

    Raises:
        typer.Exit: If neither report files nor stored runs are
            provided for analysis.
    """
    from agentbench.store import BenchmarkStore

    if from_store:
        store = BenchmarkStore(db_path=db)
        runs = store.list_runs(agent_id=agent_id, limit=100)
        if not runs:
            rprint("[yellow]No historical runs found[/yellow]")
            return
        loaded_reports = [
            ScoreReport(
                **{
                    "agent_id": r["agent_id"],
                    "agent_version": r["agent_version"],
                    "overall_score": r["overall_score"],
                    "total_tests": r["total_tests"],
                    "passed_tests": r["passed_tests"],
                    "failed_tests": r["failed_tests"],
                    "duration_seconds": r["duration_seconds"],
                    "categories": r.get("categories", []),
                    "config": r.get("config", {}),
                    "timestamp": r["timestamp"],
                    "results": [],
                }
            )
            for r in runs
        ]
    elif reports:
        loaded_reports = [_load_report(r) for r in reports]
    else:
        rprint("[red]Provide report files or use --from-store[/red]")
        raise typer.Exit(code=1)

    analyzer = TrendAnalyzer()
    trend = analyzer.build_trend(loaded_reports)

    rprint("\n[bold]Trend Analysis[/bold]\n")
    rprint(f"{'Date':<25} {'Score':<8} {'Version':<12}")
    rprint("-" * 45)
    for point in trend:
        rprint(f"{point.timestamp!s:<25} {point.overall_score:<8.1f} {point.agent_version:<12}")

    direction = analyzer.detect_trend_direction(trend)
    volatility = analyzer.volatility(trend)
    next_score = analyzer.estimate_next_score(trend)
    moving_avg = analyzer.compute_moving_average(trend)

    rprint(f"\n[bold]Direction:[/bold] {direction}")
    rprint(f"[bold]Volatility:[/bold] {volatility:.2f}")
    rprint(f"[bold]Estimated next score:[/bold] {next_score:.1f}")

    if len(moving_avg) > 1:
        rprint("\n[bold]Moving Average (window=3):[/bold]")
        for i, avg in enumerate(moving_avg):
            rprint(f"  Point {i + 1}: {avg:.1f}")


@app.command()
def store(
    command: str = typer.Argument(..., help="Command: save, list, get, clean"),
    report_file: str | None = typer.Option(None, "--report", "-r", help="Report JSON file (for save)"),
    run_id: int | None = typer.Option(None, "--id", help="Run ID (for get)"),
    agent_id: str | None = typer.Option(None, "--agent-id", "-a", help="Filter by agent ID"),
    db: str = typer.Option("agentbench.db", "--db", help="SQLite database path"),
    keep: int = typer.Option(100, "--keep", help="Runs to keep (for clean)"),
) -> None:
    """Manage benchmark results stored in a SQLite database.

    Provides commands for saving benchmark reports, listing
    stored runs, retrieving run details, and cleaning up old
    benchmark history from the local SQLite store.

    Args:
        command: Store operation to perform (save, list, get,
            or clean).
        report_file: Path to a benchmark report JSON file when
            using the save command.
        run_id: Identifier of the stored benchmark run to
            retrieve.
        agent_id: Agent identifier used to filter stored runs.
        db: Path to the SQLite database file.
        keep: Number of recent runs to retain when cleaning old
            entries.

    Returns:
        None

    Raises:
        typer.Exit: If required arguments are missing for a
            command or if an unsupported command is specified.
    """
    from agentbench.store import BenchmarkStore

    store_inst = BenchmarkStore(db_path=db)

    if command == "save":
        if not report_file:
            rprint("[red]--report file required for 'save' command[/red]")
            raise typer.Exit(code=1)
        report = _load_report(report_file)
        run_id = store_inst.save(report)
        rprint(f"[green]Saved run #{run_id}[/green]")

    elif command == "list":
        runs = store_inst.list_runs(agent_id=agent_id)
        if not runs:
            rprint("[yellow]No runs found[/yellow]")
            return
        rprint(f"\n[bold]Benchmark Runs ({len(runs)}):[/bold]\n")
        rprint(f"{'ID':<5} {'Agent':<20} {'Score':<8} {'Tests':<8} {'Date':<20}")
        rprint("-" * 61)
        for run in runs:
            rprint(f"{run['id']:<5} {run['agent_id']:<20} {run['overall_score']:<8.1f} {run['passed_tests']}/{run['total_tests']:<5} {str(run['timestamp'])[:19]:<20}")

    elif command == "get":
        if run_id is None:
            rprint("[red]--id required for 'get' command[/red]")
            raise typer.Exit(code=1)
        run_data = store_inst.get_run(run_id)
        if not run_data:
            rprint(f"[red]Run #{run_id} not found[/red]")
            return
        rprint(f"\n[bold]Run #{run_id}:[/bold]")
        rprint(f"  Agent: {run_data['agent_id']} {run_data['agent_version']}")
        rprint(f"  Score: {run_data['overall_score']:.1f}/100")
        rprint(f"  Tests: {run_data['passed_tests']}/{run_data['total_tests']} passed")
        rprint(f"  Duration: {run_data['duration_seconds']:.1f}s")
        rprint(f"  Timestamp: {run_data['timestamp']}")

    elif command == "clean":
        deleted = store_inst.delete_old_runs(keep=keep)
        rprint(f"[green]Deleted {deleted} old runs, keeping {keep}[/green]")

    else:
        rprint(f"[red]Unknown command: {command}. Use: save, list, get, clean[/red]")
        raise typer.Exit(code=1)


@app.command()
def export(
    report_file: str = typer.Argument(..., help="JSON report file to export"),
    sarif: str | None = typer.Option(None, "--sarif", help="Export to SARIF file"),
    mcpguard: str | None = typer.Option(None, "--mcpguard", help="Export MCPGuard policy YAML"),
    mcpscop: str | None = typer.Option(None, "--mcpscop", help="Export MCPscop events JSON"),
    mcpscop_findings: str | None = typer.Option(None, "--mcpscop-findings", help="Export MCPscop findings JSON"),
) -> None:
    """Export a benchmark report to external security tool formats.

    Converts a benchmark report into formats supported by
    security analysis and compliance tools, including SARIF,
    MCPGuard policies, and MCPscop event and findings exports.

    Args:
        report_file: Path to the benchmark report JSON file.
        sarif: Output path for the generated SARIF report.
        mcpguard: Output path for the generated MCPGuard policy
            YAML file.
        mcpscop: Output path for the generated MCPscop events
            JSON file.
        mcpscop_findings: Output path for the generated MCPscop
            findings JSON file.

    Returns:
        None
    """
    report_data = _load_report(report_file)

    if sarif:
        from agentbench.reporters.sarif import SARIFReporter

        path = SARIFReporter().save(report_data, sarif)
        rprint(f"[green]SARIF:[/green] {path}")

    if mcpguard:
        from agentbench.integrations.mcpguard import MCPGuardPolicyGenerator

        path = MCPGuardPolicyGenerator().save_yaml(report_data, mcpguard)
        rprint(f"[green]MCPGuard:[/green] {path}")

    if mcpscop:
        from agentbench.integrations.mcpscop import MCPscopExporter

        path = MCPscopExporter().save_events_json(report_data, mcpscop)
        rprint(f"[green]MCPscop events:[/green] {path}")

    if mcpscop_findings:
        from agentbench.integrations.mcpscop import MCPscopExporter

        path = MCPscopExporter().save_findings_json(report_data, mcpscop_findings)
        rprint(f"[green]MCPscop findings:[/green] {path}")

    if not any([sarif, mcpguard, mcpscop, mcpscop_findings]):
        rprint("[yellow]No export format specified. Use --sarif, --mcpguard, --mcpscop, or --mcpscop-findings[/yellow]")


@app.command()
def config(
    action: str = typer.Argument("show", help="Action: show, create, validate"),
    file: str = typer.Option("agentbench.yaml", "--file", "-f", help="Config file path"),
    target: str | None = typer.Option(None, "--target", "-t", help="Set target URL"),
    agent_id: str | None = typer.Option(None, "--agent-id", "-a", help="Set agent ID"),
) -> None:
    """Manage benchmark configuration files.

    Displays, creates, and validates AgentBench configuration
    files used to define benchmark settings, target endpoints,
    and agent metadata.

    Args:
        action: Configuration operation to perform (show,
            create, or validate).
        file: Path to the configuration file.
        target: Target URL to include when creating a new
            configuration file.
        agent_id: Agent identifier to include when creating a
            new configuration file.

    Returns:
        None

    Raises:
        typer.Exit: If the configuration file is missing,
            already exists when creating a new file, or an
            unsupported action is specified.
    """
    path = Path(file)

    if action == "show":
        if not path.exists():
            rprint(f"[red]Config file not found: {path}[/red]")
            raise typer.Exit(code=1)
        rprint(f"[bold]Config: {path}[/bold]")
        rprint(path.read_text())

    elif action == "create":
        if path.exists():
            rprint(f"[red]File exists: {path}. Delete it first or use a different path.[/red]")
            raise typer.Exit(code=1)
        content = f"""# AgentBench configuration
agent_id: {agent_id or "my-agent"}
target: {target or "http://localhost:8080"}
timeout: 30.0
api_format: generic
suites:
  - prompt_injection
  - tool_poisoning
  - ssrf
  - data_exfiltration
  - jailbreak
  - memory_attacks
  - multi_agent
"""
        path.write_text(content)
        rprint(f"[green]Created: {path}[/green]")

    elif action == "validate":
        _load_config(str(path))
        rprint(f"[green]Valid config: {path}[/green]")

    else:
        rprint(f"[red]Unknown action: {action}. Use: show, create, validate[/red]")
        raise typer.Exit(code=1)


@app.command()
def merge(
    files: list[str] = typer.Argument(..., help="JSON report files to merge"),
    output: str = typer.Option("merged.json", "--output", "-o", help="Output JSON file"),
    label: str = typer.Option("merged", "--label", "-l", help="Agent ID for merged report"),
) -> None:
    """Merge multiple benchmark reports into a single report.

    Combines benchmark results from multiple report files into
    a consolidated report containing aggregated scores, test
    results, and category metrics.

    Args:
        files: Paths to benchmark report JSON files to merge.
        output: Path for the generated merged report file.
        label: Agent identifier assigned to the merged report.

    Returns:
        None
    """
    from agentbench.models import ScoreCategory
    from agentbench.reporters.json import JSONReporter

    reports = [_load_report(f) for f in files]
    all_results = []
    total_passed = 0
    total_failed = 0

    cat_scores: dict[str, list[float]] = {}
    for r in reports:
        all_results.extend(r.results)
        total_passed += r.passed_tests
        total_failed += r.failed_tests
        for c in r.categories:
            cat_scores.setdefault(c.name, []).append(c.score)

    merged_cats = [
        ScoreCategory(
            name=name,
            score=sum(scores) / len(scores),
            tests_passed=reports[0].categories[0].tests_passed if reports else 0,
            tests_failed=reports[0].categories[0].tests_failed if reports else 0,
            tests_total=reports[0].categories[0].tests_total if reports else 0,
        )
        for name, scores in sorted(cat_scores.items())
    ]

    overall = sum(c.score * c.weight for c in merged_cats) / sum(c.weight for c in merged_cats) if merged_cats else 0

    merged = ScoreReport(
        agent_id=label,
        categories=merged_cats,
        overall_score=round(overall, 2),
        total_tests=sum(r.total_tests for r in reports),
        passed_tests=total_passed,
        failed_tests=total_failed,
        duration_seconds=sum(r.duration_seconds for r in reports),
        results=all_results,
    )

    json_reporter = JSONReporter()
    path = json_reporter.save(merged, output)
    rprint(f"[green]Merged {len(files)} reports -> {path}[/green]")
    rprint(f"  Overall score: {merged.overall_score:.1f}")
    rprint(f"  Total tests: {merged.total_tests} ({merged.passed_tests} passed / {merged.failed_tests} failed)")


@app.command()
def completion(
    shell: str = typer.Argument("bash", help="Shell type: bash, zsh, fish, powershell"),
) -> None:
    """Generate a shell completion script.

    Displays instructions for enabling command-line tab
    completion for the specified shell environment.

    Args:
        shell: Shell type for which completion instructions
            should be generated.

    Returns:
        None
    """
    rprint(f"# Add this to your {shell}rc:")
    rprint(f"  _AGENTBENCH_COMPLETE=source_{shell} agentbench")
    rprint("# Or run: agentbench --install-completion")


async def _send_webhook(url: str, secret: str, report: ScoreReport) -> None:
    """Send a benchmark completion notification to a webhook URL.

    Args:
        url: Webhook endpoint URL.
        secret: Secret token for webhook authentication.
        report: Completed benchmark report to send.

    Returns:
        None
    """
    from agentbench.webhooks import WebhookNotifier

    notifier = WebhookNotifier(url=url, secret=secret)
    await notifier.send(report)


def _send_webhook_sync(url: str, secret: str, report: ScoreReport) -> None:
    """Send a benchmark completion notification synchronously.

    Falls back to a synchronous HTTP POST when an async event
    loop is unavailable.

    Args:
        url: Webhook endpoint URL.
        secret: Secret token for webhook authentication.
        report: Completed benchmark report to send.

    Returns:
        None
    """
    import httpx

    try:
        payload = {
            "event": "benchmark.completed",
            "agent_id": report.agent_id,
            "overall_score": report.overall_score,
            "total_tests": report.total_tests,
            "passed_tests": report.passed_tests,
            "failed_tests": report.failed_tests,
        }
        headers = {"Content-Type": "application/json"}
        if secret:
            headers["X-Webhook-Secret"] = secret
        resp = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
        rprint(f"[green]Webhook sent (status={resp.status_code})[/green]")
    except Exception as exc:
        rprint(f"[yellow]Webhook failed: {exc}[/yellow]")


def _validate_target(url: str, api_format: str, timeout: float) -> None:
    """Validate that the target is reachable before running benchmarks.

    Args:
        url: Target URL.
        api_format: API format to validate support for.
        timeout: Request timeout in seconds.

    Returns:
        None
    """
    import asyncio as _asyncio

    from agentbench.utils.http import check_endpoint_health, mcp_initialize

    try:
        if api_format == "mcp":
            _asyncio.run(mcp_initialize(url=url, timeout=min(timeout, 10.0)))
        else:
            reachable = _asyncio.run(check_endpoint_health(url, timeout=min(timeout, 10.0)))
            if reachable:
                return
            rprint(f"[yellow]Warning: target {url} did not respond to health check. Continuing anyway...[/yellow]")
    except Exception as exc:
        rprint(f"[yellow]Warning: target validation failed ({exc}). Continuing anyway...[/yellow]")


def _resolve_report_arg(arg: str, db_path: str = "agentbench.db") -> ScoreReport:
    """Resolve a CLI argument to a ScoreReport, supporting store run IDs.

    Args:
        arg: File path or numeric store run ID (e.g., ``#42``).
        db_path: Path to SQLite database.

    Returns:
        Loaded ScoreReport.
    """
    if arg.startswith("#"):
        from agentbench.models import ScoreCategory
        from agentbench.store import BenchmarkStore

        store = BenchmarkStore(db_path=db_path)
        run_id = int(arg[1:])
        run = store.get_run(run_id)
        if not run:
            rprint(f"[red]Store run #{run_id} not found[/red]")
            raise typer.Exit(code=1)
        return ScoreReport(
            agent_id=run["agent_id"],
            agent_version=run["agent_version"],
            overall_score=run["overall_score"],
            total_tests=run["total_tests"],
            passed_tests=run["passed_tests"],
            failed_tests=run["failed_tests"],
            duration_seconds=run["duration_seconds"],
            categories=[ScoreCategory(**c) for c in run.get("categories", [])],
            timestamp=run["timestamp"],
        )

    return _load_report(arg)


def _load_config(filepath: str) -> dict[str, Any]:
    """Load and parse a YAML configuration file.

    Args:
        filepath: Path to the YAML configuration file.

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        typer.Exit: If the file is not found or exceeds the
            maximum allowed size.
    """
    import yaml

    from agentbench.utils.security import validate_file_size

    path = Path(filepath)
    if not path.exists():
        rprint(f"[red]Config file not found: {filepath}[/red]")
        raise typer.Exit(code=1)
    try:
        validate_file_size(path)
    except ValueError as exc:
        rprint(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _resolve_suites(suites_param: str) -> list[type]:
    """Resolve a suite parameter string to a list of suite classes.

    Args:
        suites_param: Comma-separated suite names or ``"all"`` to
            select every registered suite.

    Returns:
        List of suite class types matching the requested names.

    Raises:
        typer.Exit: If any requested suite name is not found in
            the registry.
    """
    if suites_param == "all":
        return [SUITE_REGISTRY[name] for name in get_suite_names()]
    names = [s.strip() for s in suites_param.split(",")]
    resolved: list[type] = []
    for name in names:
        if name not in SUITE_REGISTRY:
            rprint(f"[red]Unknown suite: {name}[/red]")
            rprint(f"Available: {', '.join(get_suite_names())}")
            raise typer.Exit(code=1)
        resolved.append(SUITE_REGISTRY[name])
    return resolved


def _parse_headers(headers: list[str]) -> dict[str, str]:
    """Parse and validate a list of raw HTTP header strings.

    Args:
        headers: List of header strings in ``"Key: Value"`` format.

    Returns:
        Dictionary mapping validated header names to their values.
    """
    from agentbench.utils.security import validate_header_value

    result: dict[str, str] = {}
    for h in headers:
        if ":" not in h:
            rprint(f"[yellow]Warning: skipping malformed header '{h}' (expected 'Key: Value')[/yellow]")
            continue
        key, value = h.split(":", 1)
        try:
            result[key.strip()] = validate_header_value(value)
        except ValueError as exc:
            rprint(f"[red]Warning: rejecting header '{key}' — {exc}[/red]")
            continue
    return result


def _load_report(filepath: str) -> ScoreReport:
    """Load and deserialize a benchmark report from a JSON file.

    Args:
        filepath: Path to the benchmark report JSON file.

    Returns:
        Deserialized ScoreReport instance.

    Raises:
        typer.Exit: If the file is not found or exceeds the
            maximum allowed size.
    """
    from agentbench.models import BenchmarkResult, BenchmarkTestCase, TestStatus
    from agentbench.utils.security import validate_file_size

    path = Path(filepath)
    if not path.exists():
        rprint(f"[red]File not found: {filepath}[/red]")
        raise typer.Exit(code=1)
    try:
        validate_file_size(path)
    except ValueError as exc:
        rprint(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)
    data = json.loads(path.read_text())

    if "results" in data and data["results"]:
        flat_results = data.pop("results")
        parsed_results: list[BenchmarkResult] = []
        for r in flat_results:
            if "test_case" not in r:
                tc = BenchmarkTestCase(
                    id=r.pop("test_id", ""),
                    name=r.pop("test_name", ""),
                    category=r.pop("category", ""),
                )
                status_str = r.pop("status", "passed")
                status = TestStatus(status_str) if status_str in {s.value for s in TestStatus} else TestStatus.PASSED
                parsed_results.append(
                    BenchmarkResult(
                        test_case=tc,
                        status=status,
                        score=r.get("score", 100.0),
                        response_time_ms=r.get("response_time_ms", 0.0),
                        detected=r.get("detected", False),
                    )
                )
            else:
                parsed_results.append(BenchmarkResult(**r))
        data["results"] = parsed_results

    return ScoreReport(**data)


if __name__ == "__main__":
    app()
