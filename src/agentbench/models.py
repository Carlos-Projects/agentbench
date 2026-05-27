"""Pydantic models for AgentBench benchmark data structures."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TestStatus(StrEnum):
    """Status of a benchmark test case execution."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class Severity(StrEnum):
    """Severity classification for benchmark findings."""

    __test__ = False  # Prevent pytest collection

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ScoreCategory(BaseModel):
    """Scores for a specific security category."""

    name: str = Field(description="Category name (e.g., prompt_injection)")
    score: float = Field(ge=0.0, le=100.0, description="Normalized score 0-100")
    weight: float = Field(default=1.0, ge=0.0, description="Category weight in overall scoring")
    tests_passed: int = Field(default=0, ge=0)
    tests_failed: int = Field(default=0, ge=0)
    tests_total: int = Field(default=0, ge=0)
    details: dict[str, Any] = Field(default_factory=dict)


class BenchmarkTestCase(BaseModel):
    """A single benchmark test case."""

    id: str = Field(description="Unique test case identifier")
    name: str = Field(description="Human-readable test name")
    category: str = Field(description="Security category")
    description: str = Field(default="")
    severity: Severity = Field(default=Severity.MEDIUM)
    target: str = Field(default="", description="Target endpoint or agent identifier")
    prompt: str = Field(default="", description="Input prompt or payload")
    expected_behavior: str = Field(default="", description="Expected secure behavior")
    tags: list[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.0)


class BenchmarkResult(BaseModel):
    """Result of executing a single test case."""

    test_case: BenchmarkTestCase
    status: TestStatus
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    response_time_ms: float = Field(default=0.0, ge=0.0)
    response: str = Field(default="")
    detected: bool = Field(default=False)
    error_message: str = Field(default="")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkSuite(BaseModel):
    """A collection of benchmark test cases for a security category."""

    name: str = Field(description="Suite name")
    category: str = Field(description="Security category")
    description: str = Field(default="")
    test_cases: list[BenchmarkTestCase] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)


class ScoreReport(BaseModel):
    """Complete scoring report for a benchmark run."""

    agent_id: str = Field(description="Agent identifier")
    agent_version: str = Field(default="")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    categories: list[ScoreCategory] = Field(default_factory=list)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_tests: int = Field(default=0)
    passed_tests: int = Field(default=0)
    failed_tests: int = Field(default=0)
    duration_seconds: float = Field(default=0.0)
    config: dict[str, Any] = Field(default_factory=dict)
    results: list[BenchmarkResult] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    """Result of comparing two or more benchmark runs."""

    baseline_id: str = Field(description="Baseline agent/run identifier")
    target_id: str = Field(description="Target agent/run identifier")
    baseline_score: float = Field(ge=0.0, le=100.0)
    target_score: float = Field(ge=0.0, le=100.0)
    score_delta: float = Field(description="Target - baseline score delta")
    category_deltas: dict[str, float] = Field(default_factory=dict)
    regression_count: int = Field(default=0)
    improvement_count: int = Field(default=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class TrendPoint(BaseModel):
    """A single data point in a security trend analysis."""

    timestamp: datetime
    overall_score: float = Field(ge=0.0, le=100.0)
    category_scores: dict[str, float] = Field(default_factory=dict)
    total_tests: int = Field(default=0)
    agent_version: str = Field(default="")


class LeaderboardEntry(BaseModel):
    """An entry in the security leaderboard."""

    rank: int = Field(default=0, ge=0)
    agent_id: str
    agent_version: str = Field(default="")
    overall_score: float = Field(ge=0.0, le=100.0)
    category_scores: dict[str, float] = Field(default_factory=dict)
    total_tests: int = Field(default=0)
    passed_tests: int = Field(default=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
