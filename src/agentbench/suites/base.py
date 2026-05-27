"""Base suite class for all benchmark suites."""

from __future__ import annotations

from abc import ABC, abstractmethod

from agentbench.models import BenchmarkSuite, BenchmarkTestCase


class BaseSuite(ABC):
    """Abstract base class for benchmark suites."""

    name: str = ""
    category: str = ""
    description: str = ""
    failure_indicators: list[str] = []

    @abstractmethod
    def generate_cases(self) -> list[BenchmarkTestCase]:
        """Generate test cases for this suite.

        Returns:
            List of benchmark test cases.
        """

    def build_suite(self) -> BenchmarkSuite:
        """Build a complete BenchmarkSuite from generated test cases.

        Returns:
            Configured BenchmarkSuite instance.
        """
        suite = BenchmarkSuite(
            name=self.name,
            category=self.category,
            description=self.description,
            test_cases=self.generate_cases(),
        )
        suite.config["failure_indicators"] = self.failure_indicators
        return suite
