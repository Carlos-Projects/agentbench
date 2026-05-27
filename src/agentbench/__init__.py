"""AgentBench: Automated benchmarking framework for evaluating AI agent security."""

__version__ = "0.2.0-dev"
__author__ = "Carlos-Projects"

from agentbench.comparison.analyzer import ComparisonAnalyzer
from agentbench.comparison.diff import ScoreDiff
from agentbench.comparison.trend import TrendAnalyzer
from agentbench.leaderboard.api import LeaderboardAPI
from agentbench.leaderboard.generator import LeaderboardGenerator
from agentbench.leaderboard.publisher import LeaderboardPublisher
from agentbench.models import (
    BenchmarkResult,
    BenchmarkSuite,
    BenchmarkTestCase,
    ComparisonResult,
    LeaderboardEntry,
    ScoreCategory,
    ScoreReport,
    Severity,
    TestStatus,
    TrendPoint,
)
from agentbench.runner import BenchmarkRunner
from agentbench.scorers.engine import ScoreEngine
from agentbench.scorers.metrics import MetricsCalculator
from agentbench.scorers.normalizer import ScoreNormalizer

__all__ = [
    "BenchmarkResult",
    "BenchmarkRunner",
    "BenchmarkSuite",
    "BenchmarkTestCase",
    "ComparisonAnalyzer",
    "ComparisonResult",
    "LeaderboardAPI",
    "LeaderboardEntry",
    "LeaderboardGenerator",
    "LeaderboardPublisher",
    "MetricsCalculator",
    "ScoreCategory",
    "ScoreDiff",
    "ScoreEngine",
    "ScoreNormalizer",
    "ScoreReport",
    "Severity",
    "TestStatus",
    "TrendAnalyzer",
    "TrendPoint",
    "__version__",
]
