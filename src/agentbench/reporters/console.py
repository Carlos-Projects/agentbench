"""Console reporter using Rich for terminal output."""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from agentbench.models import ScoreReport, TestStatus

console = Console()


class ConsoleReporter:
    """Reports benchmark results to the terminal using Rich."""

    def print_report(self, report: ScoreReport) -> None:
        """Print a complete score report to the console.

        Args:
            report: Score report to display.
        """
        self._print_header(report)
        self._print_summary(report)
        self._print_category_scores(report)
        self._print_details(report)

    def _print_header(self, report: ScoreReport) -> None:
        console.print()
        console.print(
            Panel(
                f"[bold]AgentBench Security Report[/bold]\n"
                f"Agent: {report.agent_id} {report.agent_version}\n"
                f"Timestamp: {report.timestamp.isoformat() if isinstance(report.timestamp, datetime) else report.timestamp}\n"
                f"Duration: {report.duration_seconds:.1f}s",
                title="Benchmark Results",
                border_style="blue",
            )
        )

    def _print_summary(self, report: ScoreReport) -> None:
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        with progress:
            task = progress.add_task(
                f"Overall Score: {report.overall_score:.1f}/100",
                total=100,
            )
            progress.update(task, completed=report.overall_score)

        console.print(f"\nTotal Tests: {report.total_tests}")
        console.print(f"Passed: [green]{report.passed_tests}[/green]")
        console.print(f"Failed: [red]{report.failed_tests}[/red]")

    def _print_category_scores(self, report: ScoreReport) -> None:
        table = Table(title="Category Scores", box=None)
        table.add_column("Category", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Passed", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Total", justify="right")

        for cat in report.categories:
            score_style = "green" if cat.score >= 80 else "yellow" if cat.score >= 50 else "red"
            table.add_row(
                cat.name,
                f"[{score_style}]{cat.score:.1f}[/{score_style}]",
                str(cat.tests_passed),
                str(cat.tests_failed),
                str(cat.tests_total),
            )

        console.print()
        console.print(table)

    def _print_details(self, report: ScoreReport) -> None:
        if not report.results:
            return

        table = Table(title="Test Case Details", box=None)
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Score", justify="right")

        for result in report.results:
            status_style = {
                TestStatus.PASSED: "green",
                TestStatus.FAILED: "red",
                TestStatus.ERROR: "red",
                TestStatus.SKIPPED: "yellow",
                TestStatus.TIMEOUT: "yellow",
            }.get(result.status, "white")

            table.add_row(
                result.test_case.id,
                result.test_case.name,
                f"[{status_style}]{result.status.value}[/{status_style}]",
                f"{result.score:.1f}",
            )

        console.print()
        console.print(table)

    def print_comparison(self, baseline: ScoreReport, target: ScoreReport) -> None:
        """Print a comparison between two reports.

        Args:
            baseline: Baseline score report.
            target: Target score report.
        """
        table = Table(title="Score Comparison", box=None)
        table.add_column("Metric", style="cyan")
        table.add_column(f"Baseline ({baseline.agent_id})", justify="right")
        table.add_column(f"Target ({target.agent_id})", justify="right")
        table.add_column("Delta", justify="right")

        delta = target.overall_score - baseline.overall_score
        delta_style = "green" if delta >= 0 else "red"

        table.add_row(
            "Overall Score",
            f"{baseline.overall_score:.1f}",
            f"{target.overall_score:.1f}",
            f"[{delta_style}]{delta:+.1f}[/{delta_style}]",
        )

        baseline_cats = {c.name: c.score for c in baseline.categories}
        target_cats = {c.name: c.score for c in target.categories}

        for cat in sorted(set(baseline_cats) | set(target_cats)):
            b_score = baseline_cats.get(cat, 0.0)
            t_score = target_cats.get(cat, 0.0)
            d = t_score - b_score
            d_style = "green" if d >= 0 else "red"

            table.add_row(
                f"  {cat}",
                f"{b_score:.1f}",
                f"{t_score:.1f}",
                f"[{d_style}]{d:+.1f}[/{d_style}]",
            )

        console.print()
        console.print(table)
